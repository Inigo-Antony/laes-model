"""
LAES Transient Simulation Module
================================

Time-domain simulation of LAES operation.

Author: [Your Name]
License: MIT
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
import matplotlib.pyplot as plt

from .config import PlantConfig, SECONDS_PER_HOUR
from .thermodynamics import calculate_liquefaction, calculate_discharge
from .storage import ThermalStorage, LiquidAirTank


@dataclass
class TimeStepData:
    """Data recorded at each simulation time step"""
    time_hours: float
    mode: str  # 'charge', 'discharge', or 'idle'
    
    # Power [kW]
    power_in_kW: float = 0
    power_out_kW: float = 0
    
    # Tank state
    tank_level_pct: float = 0
    
    # Thermal storage states
    hot_soc_pct: float = 0
    cold_soc_pct: float = 0
    
    # Mass flows [kg]
    liquid_produced_kg: float = 0
    liquid_consumed_kg: float = 0
    boiloff_kg: float = 0
    
    # Energy flows [kWh]
    energy_in_kWh: float = 0
    energy_out_kWh: float = 0


class LAESSimulator:
    """
    Transient LAES system simulator.
    
    Simulates operation over time including:
    - Charge/discharge cycles
    - Storage losses
    - Cold recycle between cycles
    - Mass and energy balance
    
    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    
    Attributes
    ----------
    history : List[TimeStepData]
        Time series of simulation results
    total_energy_in_kWh : float
        Cumulative energy input
    total_energy_out_kWh : float
        Cumulative energy output
    
    Example
    -------
    >>> config = PlantConfig(charge_power_MW=10, discharge_power_MW=10)
    >>> sim = LAESSimulator(config)
    >>> schedule = [('charge', 8), ('idle', 4), ('discharge', 6), ('idle', 6)]
    >>> results = sim.run(schedule)
    >>> sim.plot_results('simulation.png')
    """
    
    def __init__(self, cfg: PlantConfig):
        self.cfg = cfg
        
        # Pre-calculate cycle performance
        self.liq_no_cold = calculate_liquefaction(cfg, cold_available_J_per_kg=0)
        self.discharge_perf = calculate_discharge(cfg)
        
        # Key specific values (per kg liquid air)
        self.specific_consumption = self.liq_no_cold['specific_consumption_J_per_kg']
        self.specific_output = self.discharge_perf['net_work_J_per_kg']
        self.heat_per_kg_discharge = self.discharge_perf['heat_consumed_J_per_kg']
        self.cold_per_kg = self.discharge_perf['cold_recoverable_J_per_kg']
        
        # Initialize storage
        self._init_storage()
        
        # Results
        self.history: List[TimeStepData] = []
        self.total_energy_in_kWh = 0
        self.total_energy_out_kWh = 0
    
    def _init_storage(self):
        """Initialize storage systems with proper sizing"""
        cfg = self.cfg
        
        # Liquid air tank
        self.tank = LiquidAirTank(
            capacity_kg=cfg.tank_capacity_kg,
            min_level_frac=cfg.tank_min_level_pct / 100,
            boiloff_rate_per_s=cfg.boiloff_rate_per_s
        )
        
        # Hot storage: sized for one full discharge
        liquid_rate_discharge = cfg.discharge_power_kW * 1000 / self.specific_output
        hot_capacity_J = (
            self.heat_per_kg_discharge *
            liquid_rate_discharge *
            cfg.storage_duration_hours *
            SECONDS_PER_HOUR * 1.5  # 50% margin
        )
        
        self.hot_storage = ThermalStorage(
            capacity_J=hot_capacity_J,
            loss_rate_per_s=cfg.hot_loss_rate_per_s,
            efficiency=cfg.hot_storage_efficiency
        )
        
        # Cold storage: sized for cold recycle benefit
        cold_capacity_J = self.cold_per_kg * cfg.tank_capacity_kg * 0.5
        
        self.cold_storage = ThermalStorage(
            capacity_J=cold_capacity_J,
            loss_rate_per_s=cfg.cold_loss_rate_per_s,
            efficiency=cfg.cold_storage_efficiency
        )
    
    def reset(self, initial_tank_pct: float = 50.0):
        """
        Reset simulator to initial conditions.
        
        Parameters
        ----------
        initial_tank_pct : float
            Initial tank fill level [%]
        """
        self._init_storage()
        self.history = []
        self.total_energy_in_kWh = 0
        self.total_energy_out_kWh = 0
        
        # Set initial conditions
        self.tank.mass_kg = initial_tank_pct / 100 * self.cfg.tank_capacity_kg
        self.hot_storage.energy_J = self.hot_storage.capacity_J * 0.5
        self.cold_storage.energy_J = 0
    
    def run(
        self,
        schedule: List[Tuple[str, float]],
        dt_hours: float = 1.0,
        initial_tank_pct: float = 50.0,
        verbose: bool = True
    ) -> Dict:
        """
        Run simulation with given schedule.
        
        Parameters
        ----------
        schedule : List[Tuple[str, float]]
            List of (mode, duration_hours) tuples
            mode = 'charge', 'discharge', or 'idle'
        dt_hours : float
            Time step [hours]
        initial_tank_pct : float
            Initial tank level [%]
        verbose : bool
            Print progress
        
        Returns
        -------
        dict
            Simulation results
        """
        self.reset(initial_tank_pct)
        dt_seconds = dt_hours * SECONDS_PER_HOUR
        
        if verbose:
            print(f"\n{'═'*60}")
            print(f" TRANSIENT SIMULATION")
            print(f"{'═'*60}")
            print(f" Time step: {dt_hours} hours")
            print(f" Schedule: {len(schedule)} phases")
        
        current_time = 0
        
        for phase_mode, phase_duration in schedule:
            n_steps = int(phase_duration / dt_hours)
            
            if verbose:
                print(f"\n Phase: {phase_mode.upper()} for {phase_duration} hours")
            
            for _ in range(n_steps):
                step_data = self._execute_step(phase_mode, dt_seconds, current_time)
                self.history.append(step_data)
                current_time += dt_hours
        
        return self._calculate_results(verbose)
    
    def _execute_step(self, mode: str, dt_s: float, time_h: float) -> TimeStepData:
        """Execute a single time step"""
        
        step = TimeStepData(time_hours=time_h, mode=mode)
        dt_hours = dt_s / SECONDS_PER_HOUR
        
        if mode == 'charge':
            self._execute_charge(step, dt_s, dt_hours)
        elif mode == 'discharge':
            self._execute_discharge(step, dt_s, dt_hours)
        
        # Apply losses (always)
        step.boiloff_kg = self.tank.apply_boiloff(dt_s)
        self.hot_storage.apply_losses(dt_s)
        self.cold_storage.apply_losses(dt_s)
        
        # Record final states
        step.tank_level_pct = self.tank.level * 100
        step.hot_soc_pct = self.hot_storage.soc * 100
        step.cold_soc_pct = self.cold_storage.soc * 100
        
        return step
    
    def _execute_charge(self, step: TimeStepData, dt_s: float, dt_hours: float):
        """Execute charging time step"""
        power_kW = self.cfg.charge_power_kW
        step.power_in_kW = power_kW
        
        # Calculate cold available from storage
        liq_no_cold = self.liq_no_cold
        air_rate_kg_s = power_kW * 1000 / liq_no_cold['net_work_J_per_kg']
        air_processed_kg = air_rate_kg_s * dt_s
        
        if self.cold_storage.energy_J > 0 and air_processed_kg > 0:
            cold_per_kg = min(
                self.cold_storage.energy_J / air_processed_kg,
                150000  # Cap at 150 kJ/kg
            )
        else:
            cold_per_kg = 0
        
        # Calculate liquefaction with cold
        liq_result = calculate_liquefaction(self.cfg, cold_available_J_per_kg=cold_per_kg)
        
        # Mass flows
        energy_in_J = power_kW * 1000 * dt_s
        air_processed = energy_in_J / liq_result['net_work_J_per_kg']
        liquid_produced = air_processed * liq_result['liquid_yield']
        
        # Update tank
        actually_stored = self.tank.charge(liquid_produced)
        step.liquid_produced_kg = actually_stored
        
        # Store compression heat
        heat_J = liq_result['heat_rejected_J_per_kg'] * air_processed
        self.hot_storage.charge(heat_J)
        
        # Use cold from storage
        cold_used_J = liq_result['cold_used_J_per_kg'] * air_processed
        self.cold_storage.discharge(cold_used_J)
        
        # Track energy
        step.energy_in_kWh = power_kW * dt_hours
        self.total_energy_in_kWh += step.energy_in_kWh
    
    def _execute_discharge(self, step: TimeStepData, dt_s: float, dt_hours: float):
        """Execute discharging time step"""
        target_power_kW = self.cfg.discharge_power_kW
        
        # Required liquid air rate
        liquid_rate_kg_s = target_power_kW * 1000 / self.specific_output
        liquid_needed = liquid_rate_kg_s * dt_s
        
        # Get from tank
        liquid_consumed = self.tank.discharge(liquid_needed)
        step.liquid_consumed_kg = liquid_consumed
        
        # Actual power (may be limited by tank)
        power_fraction = liquid_consumed / liquid_needed if liquid_needed > 0 else 0
        actual_power_kW = target_power_kW * power_fraction
        step.power_out_kW = actual_power_kW
        
        # Use heat from storage
        heat_needed_J = self.heat_per_kg_discharge * liquid_consumed
        heat_delivered = self.hot_storage.discharge(heat_needed_J)
        
        # Check heat availability
        if heat_delivered < heat_needed_J * 0.9 and heat_needed_J > 0:
            heat_fraction = heat_delivered / heat_needed_J
            actual_power_kW *= heat_fraction
            step.power_out_kW = actual_power_kW
        
        # Store cold for next cycle
        cold_generated_J = self.cold_per_kg * liquid_consumed
        self.cold_storage.charge(cold_generated_J)
        
        # Track energy
        step.energy_out_kWh = actual_power_kW * dt_hours
        self.total_energy_out_kWh += step.energy_out_kWh
    
    def _calculate_results(self, verbose: bool) -> Dict:
        """Calculate simulation results"""
        
        # Round-trip efficiency
        rte = (
            self.total_energy_out_kWh / self.total_energy_in_kWh
            if self.total_energy_in_kWh > 0 else 0
        )
        
        # Storage efficiencies
        tank_eff = 1 - (
            self.tank.total_boiloff_kg / max(self.tank.total_charged_kg, 1)
        )
        hot_eff = 1 - (
            self.hot_storage.total_lost_J / max(self.hot_storage.total_charged_J, 1)
        )
        cold_eff = 1 - (
            self.cold_storage.total_lost_J / max(self.cold_storage.total_charged_J, 1)
        )
        
        results = {
            'total_energy_in_kWh': self.total_energy_in_kWh,
            'total_energy_out_kWh': self.total_energy_out_kWh,
            'round_trip_efficiency': rte,
            'tank_efficiency': tank_eff,
            'hot_storage_efficiency': hot_eff,
            'cold_storage_efficiency': cold_eff,
            'total_liquid_produced_kg': self.tank.total_charged_kg,
            'total_liquid_consumed_kg': self.tank.total_discharged_kg,
            'total_boiloff_kg': self.tank.total_boiloff_kg,
            'final_tank_level_pct': self.tank.level * 100,
        }
        
        if verbose:
            print(f"\n{'═'*60}")
            print(f" SIMULATION RESULTS")
            print(f"{'═'*60}")
            print(f"\n Energy Balance:")
            print(f"   Energy in:  {self.total_energy_in_kWh:.1f} kWh")
            print(f"   Energy out: {self.total_energy_out_kWh:.1f} kWh")
            print(f"   Round-trip efficiency: {rte:.1%}")
            print(f"\n Mass Balance:")
            print(f"   Liquid produced:  {self.tank.total_charged_kg:.0f} kg")
            print(f"   Liquid consumed:  {self.tank.total_discharged_kg:.0f} kg")
            print(f"   Boil-off losses:  {self.tank.total_boiloff_kg:.1f} kg")
            print(f"\n Storage Efficiencies:")
            print(f"   Tank:        {tank_eff:.1%}")
            print(f"   Hot storage: {hot_eff:.1%}")
            print(f"   Cold storage: {cold_eff:.1%}")
        
        return results
    
    def plot_results(self, save_path: str = None, show: bool = True) -> plt.Figure:
        """
        Generate visualization of simulation results.
        
        Parameters
        ----------
        save_path : str, optional
            Path to save figure
        show : bool
            Display figure interactively
        
        Returns
        -------
        matplotlib.figure.Figure
            Generated figure
        """
        if not self.history:
            print("No data to plot. Run simulation first.")
            return None
        
        times = [s.time_hours for s in self.history]
        
        fig, axes = plt.subplots(4, 1, figsize=(12, 12), sharex=True)
        
        # Plot 1: Tank level and power
        ax1 = axes[0]
        ax1_twin = ax1.twinx()
        
        tank_levels = [s.tank_level_pct for s in self.history]
        power_in = [s.power_in_kW for s in self.history]
        power_out = [-s.power_out_kW for s in self.history]
        
        ax1.fill_between(times, tank_levels, alpha=0.3, color='blue', label='Tank Level')
        ax1.plot(times, tank_levels, 'b-', linewidth=2)
        ax1.set_ylabel('Tank Level (%)', color='blue')
        ax1.set_ylim(0, 100)
        ax1.tick_params(axis='y', labelcolor='blue')
        
        for t, p_in, p_out in zip(times, power_in, power_out):
            if p_in > 0:
                ax1_twin.bar(t, p_in, width=0.8, color='green', alpha=0.6)
            if p_out < 0:
                ax1_twin.bar(t, p_out, width=0.8, color='red', alpha=0.6)
        
        ax1_twin.axhline(y=0, color='black', linewidth=0.5)
        ax1_twin.set_ylabel('Power (kW)')
        ax1.set_title('Tank Level and Power Flow')
        ax1.legend(loc='upper left')
        ax1.grid(alpha=0.3)
        
        # Plot 2: Thermal storage
        ax2 = axes[1]
        hot_soc = [s.hot_soc_pct for s in self.history]
        cold_soc = [s.cold_soc_pct for s in self.history]
        
        ax2.plot(times, hot_soc, 'r-', linewidth=2, label='Hot Storage')
        ax2.plot(times, cold_soc, 'b-', linewidth=2, label='Cold Storage')
        ax2.fill_between(times, hot_soc, alpha=0.2, color='red')
        ax2.fill_between(times, cold_soc, alpha=0.2, color='blue')
        ax2.set_ylabel('State of Charge (%)')
        ax2.set_ylim(0, 105)
        ax2.legend()
        ax2.set_title('Thermal Storage State of Charge')
        ax2.grid(alpha=0.3)
        
        # Plot 3: Mass flows
        ax3 = axes[2]
        liquid_prod = [s.liquid_produced_kg for s in self.history]
        liquid_cons = [s.liquid_consumed_kg for s in self.history]
        
        ax3.bar(times, liquid_prod, width=0.8, color='green', alpha=0.6, label='Produced')
        ax3.bar(times, [-l for l in liquid_cons], width=0.8, color='red', alpha=0.6, label='Consumed')
        ax3.axhline(y=0, color='black', linewidth=0.5)
        ax3.set_ylabel('Liquid Air (kg/step)')
        ax3.legend()
        ax3.set_title('Liquid Air Mass Flows')
        ax3.grid(alpha=0.3)
        
        # Plot 4: Cumulative energy
        ax4 = axes[3]
        cum_in = np.cumsum([s.energy_in_kWh for s in self.history])
        cum_out = np.cumsum([s.energy_out_kWh for s in self.history])
        
        ax4.plot(times, cum_in, 'g-', linewidth=2, label='Energy In')
        ax4.plot(times, cum_out, 'r-', linewidth=2, label='Energy Out')
        ax4.fill_between(times, cum_in, alpha=0.2, color='green')
        ax4.fill_between(times, cum_out, alpha=0.2, color='red')
        ax4.set_xlabel('Time (hours)')
        ax4.set_ylabel('Energy (kWh)')
        ax4.legend()
        ax4.set_title('Cumulative Energy Flow')
        ax4.grid(alpha=0.3)
        
        # Add RTE annotation
        if cum_in[-1] > 0:
            rte = cum_out[-1] / cum_in[-1]
            ax4.annotate(
                f'RTE = {rte:.1%}',
                xy=(times[-1] * 0.7, cum_out[-1] * 0.8),
                fontsize=12,
                fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5)
            )
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"\nPlot saved to {save_path}")
        
        if show:
            plt.show()
        else:
            plt.close()
        
        return fig
