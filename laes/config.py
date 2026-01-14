"""
LAES Configuration Module
=========================

All configurable parameters for the LAES model.

Author: [Your Name]
License: MIT
"""

from dataclasses import dataclass


# Physical constants
SECONDS_PER_HOUR = 3600
HOURS_PER_DAY = 24
HOURS_PER_YEAR = 8760
T_LIQUID_AIR_K = 78.9       # Boiling point at 1 atm [K]
RHO_LIQUID_AIR = 875.0      # Density of liquid air [kg/m³]


@dataclass
class PlantConfig:
    """
    Complete LAES plant configuration.
    
    All parameters needed to define a LAES system including:
    - Plant sizing (power, duration, tank)
    - Cycle parameters (pressures, temperatures, efficiencies)
    - Thermal storage parameters
    - Economic assumptions
    
    Example
    -------
    >>> config = PlantConfig(
    ...     charge_power_MW=50,
    ...     discharge_power_MW=50,
    ...     storage_duration_hours=6,
    ...     tank_capacity_tonnes=1000,
    ... )
    """
    
    # ═══════════════════════════════════════════════════════════════════════
    # PLANT SIZING
    # ═══════════════════════════════════════════════════════════════════════
    
    charge_power_MW: float = 10.0
    """Charging (liquefaction) power input [MW]"""
    
    discharge_power_MW: float = 10.0
    """Discharge (power recovery) power output [MW]"""
    
    storage_duration_hours: float = 4.0
    """Nominal storage duration at full discharge [hours]"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # TANK CONFIGURATION
    # ═══════════════════════════════════════════════════════════════════════
    
    tank_capacity_tonnes: float = 200.0
    """Liquid air tank capacity [tonnes]"""
    
    tank_min_level_pct: float = 10.0
    """Minimum tank level for pump NPSH [%]"""
    
    boiloff_pct_per_day: float = 0.2
    """Tank boil-off rate [%/day]"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # CYCLE PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════
    
    P_charge_bar: float = 50.0
    """Liquefaction cycle high pressure [bar]"""
    
    P_discharge_bar: float = 70.0
    """Power cycle high pressure [bar]"""
    
    T_ambient_C: float = 25.0
    """Ambient temperature [°C]"""
    
    T_superheat_C: float = 200.0
    """Turbine inlet temperature [°C]"""
    
    n_compressor_stages: int = 3
    """Number of compression stages"""
    
    n_turbine_stages: int = 2
    """Number of turbine stages (with reheat)"""
    
    bypass_fraction: float = 0.60
    """Fraction of flow through bypass turbine (Claude cycle)"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # COMPONENT EFFICIENCIES
    # ═══════════════════════════════════════════════════════════════════════
    
    eta_compressor: float = 0.85
    """Compressor isentropic efficiency"""
    
    eta_cryo_turbine: float = 0.80
    """Cryogenic (bypass) turbine isentropic efficiency"""
    
    eta_turbine: float = 0.85
    """Power turbine isentropic efficiency"""
    
    eta_pump: float = 0.75
    """Cryogenic pump efficiency"""
    
    hx_effectiveness: float = 0.90
    """Heat exchanger effectiveness"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # THERMAL STORAGE
    # ═══════════════════════════════════════════════════════════════════════
    
    hot_storage_loss_pct_per_day: float = 2.0
    """Hot storage heat loss rate [%/day]"""
    
    hot_storage_efficiency: float = 0.90
    """Hot storage round-trip efficiency"""
    
    cold_storage_loss_pct_per_day: float = 5.0
    """Cold storage heat gain rate [%/day]"""
    
    cold_storage_efficiency: float = 0.85
    """Cold storage round-trip efficiency"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # ECONOMICS
    # ═══════════════════════════════════════════════════════════════════════
    
    price_offpeak_MWh: float = 30.0
    """Off-peak electricity price for charging [$/MWh]"""
    
    price_onpeak_MWh: float = 80.0
    """On-peak electricity price for discharge [$/MWh]"""
    
    discount_rate: float = 0.08
    """Real discount rate for NPV calculations"""
    
    project_years: int = 25
    """Project lifetime [years]"""
    
    # ═══════════════════════════════════════════════════════════════════════
    # DERIVED PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════
    
    @property
    def charge_power_kW(self) -> float:
        """Charging power [kW]"""
        return self.charge_power_MW * 1000
    
    @property
    def discharge_power_kW(self) -> float:
        """Discharge power [kW]"""
        return self.discharge_power_MW * 1000
    
    @property
    def storage_capacity_MWh(self) -> float:
        """Nominal storage capacity [MWh]"""
        return self.discharge_power_MW * self.storage_duration_hours
    
    @property
    def tank_capacity_kg(self) -> float:
        """Tank capacity [kg]"""
        return self.tank_capacity_tonnes * 1000
    
    @property
    def tank_capacity_m3(self) -> float:
        """Tank capacity [m³]"""
        return self.tank_capacity_kg / RHO_LIQUID_AIR
    
    @property
    def P_charge_Pa(self) -> float:
        """Liquefaction pressure [Pa]"""
        return self.P_charge_bar * 1e5
    
    @property
    def P_discharge_Pa(self) -> float:
        """Power cycle pressure [Pa]"""
        return self.P_discharge_bar * 1e5
    
    @property
    def P_ambient_Pa(self) -> float:
        """Ambient pressure [Pa]"""
        return 101325.0
    
    @property
    def T_ambient_K(self) -> float:
        """Ambient temperature [K]"""
        return self.T_ambient_C + 273.15
    
    @property
    def T_superheat_K(self) -> float:
        """Turbine inlet temperature [K]"""
        return self.T_superheat_C + 273.15
    
    @property
    def T_intercool_K(self) -> float:
        """Intercooler outlet temperature [K]"""
        return 308.15  # 35°C
    
    @property
    def boiloff_rate_per_s(self) -> float:
        """Boil-off rate [1/s]"""
        return (self.boiloff_pct_per_day / 100) / (HOURS_PER_DAY * SECONDS_PER_HOUR)
    
    @property
    def hot_loss_rate_per_s(self) -> float:
        """Hot storage loss rate [1/s]"""
        return (self.hot_storage_loss_pct_per_day / 100) / (HOURS_PER_DAY * SECONDS_PER_HOUR)
    
    @property
    def cold_loss_rate_per_s(self) -> float:
        """Cold storage loss rate [1/s]"""
        return (self.cold_storage_loss_pct_per_day / 100) / (HOURS_PER_DAY * SECONDS_PER_HOUR)
    
    def summary(self) -> str:
        """Return formatted configuration summary"""
        return f"""
LAES Configuration Summary
══════════════════════════════════════════════════════════════
Plant Size:
  Charge Power:     {self.charge_power_MW:.1f} MW
  Discharge Power:  {self.discharge_power_MW:.1f} MW
  Storage Duration: {self.storage_duration_hours:.1f} hours
  Storage Capacity: {self.storage_capacity_MWh:.1f} MWh

Tank:
  Capacity:         {self.tank_capacity_tonnes:.0f} tonnes ({self.tank_capacity_m3:.0f} m³)
  Min Level:        {self.tank_min_level_pct:.0f}%
  Boil-off Rate:    {self.boiloff_pct_per_day:.2f}%/day

Cycle Parameters:
  Charge Pressure:    {self.P_charge_bar:.0f} bar
  Discharge Pressure: {self.P_discharge_bar:.0f} bar
  Superheat Temp:     {self.T_superheat_C:.0f}°C
  Compressor η:       {self.eta_compressor:.0%}
  Turbine η:          {self.eta_turbine:.0%}

Thermal Storage:
  Hot Storage Loss:   {self.hot_storage_loss_pct_per_day:.1f}%/day
  Cold Storage Loss:  {self.cold_storage_loss_pct_per_day:.1f}%/day

Economics:
  Off-peak Price:     ${self.price_offpeak_MWh:.0f}/MWh
  On-peak Price:      ${self.price_onpeak_MWh:.0f}/MWh
  Price Spread:       ${self.price_onpeak_MWh - self.price_offpeak_MWh:.0f}/MWh
  Discount Rate:      {self.discount_rate:.0%}
  Project Life:       {self.project_years} years
══════════════════════════════════════════════════════════════
"""


# ═══════════════════════════════════════════════════════════════════════════════
# PREDEFINED SCHEDULES
# ═══════════════════════════════════════════════════════════════════════════════

SCHEDULES = {
    'default': [
        ('charge', 8),
        ('idle', 4),
        ('discharge', 4),
        ('idle', 4),
        ('discharge', 2),
        ('idle', 2),
    ],
    'two_day': [
        ('discharge', 4),
        ('idle', 4),
        ('charge', 8),
        ('idle', 8),
        ('discharge', 4),
        ('idle', 4),
        ('charge', 8),
        ('idle', 8),
    ],
    'peak_shaving': [
        ('charge', 8),
        ('idle', 4),
        ('discharge', 2),
        ('idle', 2),
        ('discharge', 2),
        ('idle', 2),
        ('discharge', 2),
        ('idle', 2),
    ],
}
"""Predefined operating schedules: list of (mode, duration_hours) tuples"""
