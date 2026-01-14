"""
LAES Package Tests
==================

Run with: pytest tests/test_laes.py -v
Or:       python -m pytest tests/ -v

Author: [Your Name]
"""

import pytest
import numpy as np

from laes import (
    PlantConfig,
    calculate_liquefaction,
    calculate_discharge,
    calculate_rte,
    ThermalStorage,
    LiquidAirTank,
    LAESSimulator,
    calculate_economics,
    calculate_capex,
    SCHEDULES,
)


# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    """Test PlantConfig class"""

    def test_default_values(self):
        """Test default configuration values"""
        cfg = PlantConfig()
        assert cfg.charge_power_MW == 10.0
        assert cfg.discharge_power_MW == 10.0
        assert cfg.storage_duration_hours == 4.0
        assert cfg.tank_capacity_tonnes == 200.0

    def test_custom_values(self):
        """Test custom configuration"""
        cfg = PlantConfig(
            charge_power_MW=50,
            discharge_power_MW=50,
            storage_duration_hours=6,
        )
        assert cfg.charge_power_MW == 50
        assert cfg.storage_duration_hours == 6

    def test_derived_properties(self):
        """Test derived property calculations"""
        cfg = PlantConfig(charge_power_MW=50, storage_duration_hours=6)
        assert cfg.charge_power_kW == 50000
        assert cfg.storage_capacity_MWh == 300  # 50 * 6

    def test_unit_conversions(self):
        """Test temperature and pressure conversions"""
        cfg = PlantConfig(T_ambient_C=25, P_charge_bar=50)
        assert cfg.T_ambient_K == 298.15
        assert cfg.P_charge_Pa == 5e6

    def test_tank_conversions(self):
        """Test tank capacity conversions"""
        cfg = PlantConfig(tank_capacity_tonnes=100)
        assert cfg.tank_capacity_kg == 100000

    def test_loss_rates(self):
        """Test loss rate conversions"""
        cfg = PlantConfig(boiloff_pct_per_day=0.2)
        # Should be small positive number
        assert cfg.boiloff_rate_per_s > 0
        assert cfg.boiloff_rate_per_s < 1e-6


# ══════════════════════════════════════════════════════════════════════════════
# THERMODYNAMICS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestThermodynamics:
    """Test thermodynamic calculations"""

    def test_liquefaction_basic(self):
        """Test basic liquefaction cycle"""
        cfg = PlantConfig()
        result = calculate_liquefaction(cfg, cold_available_J_per_kg=0)

        # Check all expected keys exist
        assert 'liquid_yield' in result
        assert 'specific_consumption_J_per_kg' in result
        assert 'specific_consumption_kWh_per_kg' in result

        # Check physical bounds
        assert 0 < result['liquid_yield'] < 1
        assert result['specific_consumption_J_per_kg'] > 0

    def test_liquefaction_with_cold_improves_yield(self):
        """Test that cold recycle improves performance"""
        cfg = PlantConfig()

        result_no_cold = calculate_liquefaction(cfg, cold_available_J_per_kg=0)
        result_with_cold = calculate_liquefaction(cfg, cold_available_J_per_kg=100000)

        # Cold recycle should improve yield
        assert result_with_cold['liquid_yield'] > result_no_cold['liquid_yield']

        # And reduce specific consumption
        assert (result_with_cold['specific_consumption_J_per_kg'] <
                result_no_cold['specific_consumption_J_per_kg'])

    def test_discharge_cycle(self):
        """Test discharge cycle calculations"""
        cfg = PlantConfig()
        result = calculate_discharge(cfg)

        # Check expected keys
        assert 'net_work_J_per_kg' in result
        assert 'cold_recoverable_J_per_kg' in result
        assert 'heat_consumed_J_per_kg' in result

        # Physical checks
        assert result['net_work_J_per_kg'] > 0
        assert result['cold_recoverable_J_per_kg'] > 0
        assert result['turbine_work_J_per_kg'] > result['pump_work_J_per_kg']

    def test_rte_bounds(self):
        """Test RTE is within physical bounds"""
        cfg = PlantConfig()
        result = calculate_rte(cfg)

        # RTE must be between 0 and 1
        assert 0 < result['rte_no_cold'] < 1
        assert 0 < result['rte_with_cold'] < 1

        # Cold recycle should improve RTE
        assert result['rte_with_cold'] > result['rte_no_cold']

    def test_rte_typical_range(self):
        """Test RTE falls in expected range for LAES"""
        cfg = PlantConfig()
        result = calculate_rte(cfg)

        # LAES typically achieves 25-60% RTE
        assert 0.20 < result['rte_with_cold'] < 0.70

    def test_efficiency_impact(self):
        """Test that better efficiencies improve RTE"""
        cfg_low = PlantConfig(eta_compressor=0.75, eta_turbine=0.75)
        cfg_high = PlantConfig(eta_compressor=0.90, eta_turbine=0.90)

        rte_low = calculate_rte(cfg_low)['rte_with_cold']
        rte_high = calculate_rte(cfg_high)['rte_with_cold']

        assert rte_high > rte_low


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestThermalStorage:
    """Test ThermalStorage class"""

    def test_initialization(self):
        """Test storage initialization"""
        storage = ThermalStorage(capacity_J=1e9, loss_rate_per_s=0, efficiency=1.0)
        assert storage.capacity_J == 1e9
        assert storage.energy_J == 0
        assert storage.soc == 0

    def test_charging(self):
        """Test charging operation"""
        storage = ThermalStorage(capacity_J=1e9, loss_rate_per_s=0, efficiency=1.0)
        storage.charge(5e8)
        assert storage.soc == pytest.approx(0.5, rel=0.01)

    def test_discharging(self):
        """Test discharging operation"""
        storage = ThermalStorage(capacity_J=1e9, loss_rate_per_s=0, efficiency=1.0)
        storage.charge(1e9)
        storage.discharge(5e8)
        assert storage.soc == pytest.approx(0.5, rel=0.01)

    def test_overflow(self):
        """Test overflow handling"""
        storage = ThermalStorage(capacity_J=1e9, loss_rate_per_s=0, efficiency=1.0)
        storage.charge(1.5e9)  # More than capacity
        assert storage.soc == pytest.approx(1.0, rel=0.01)
        assert storage.overflow_J > 0

    def test_efficiency_losses(self):
        """Test round-trip efficiency losses"""
        storage = ThermalStorage(capacity_J=1e9, loss_rate_per_s=0, efficiency=0.81)
        storage.charge(1e9)
        delivered = storage.discharge(1e9)
        # Should get back ~81% due to efficiency
        assert delivered < 1e9
        assert delivered == pytest.approx(0.81e9, rel=0.05)

    def test_time_losses(self):
        """Test time-based losses"""
        storage = ThermalStorage(capacity_J=1e9, loss_rate_per_s=1e-5, efficiency=1.0)
        storage.energy_J = 1e9
        initial = storage.energy_J
        storage.apply_losses(3600)  # 1 hour
        assert storage.energy_J < initial


class TestLiquidAirTank:
    """Test LiquidAirTank class"""

    def test_initialization(self):
        """Test tank initialization"""
        tank = LiquidAirTank(capacity_kg=100000, min_level_frac=0.1, boiloff_rate_per_s=0)
        assert tank.capacity_kg == 100000
        assert tank.mass_kg == 0
        assert tank.level == 0

    def test_charging(self):
        """Test tank charging"""
        tank = LiquidAirTank(capacity_kg=100000, min_level_frac=0.1, boiloff_rate_per_s=0)
        tank.charge(50000)
        assert tank.level == pytest.approx(0.5, rel=0.01)

    def test_min_level(self):
        """Test minimum level enforcement"""
        tank = LiquidAirTank(capacity_kg=100000, min_level_frac=0.1, boiloff_rate_per_s=0)
        tank.charge(50000)
        # Try to discharge everything, but min level prevents it
        discharged = tank.discharge(100000)
        assert discharged == pytest.approx(40000, rel=0.01)  # 50000 - 10000 min

    def test_boiloff(self):
        """Test boil-off calculation"""
        tank = LiquidAirTank(capacity_kg=100000, min_level_frac=0.1, boiloff_rate_per_s=1e-6)
        tank.mass_kg = 50000
        lost = tank.apply_boiloff(3600)  # 1 hour
        assert lost > 0
        assert tank.mass_kg < 50000


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestSimulation:
    """Test LAESSimulator class"""

    def test_simulation_runs(self):
        """Test that simulation completes without errors"""
        cfg = PlantConfig()
        sim = LAESSimulator(cfg)
        schedule = [('charge', 4), ('discharge', 2)]
        results = sim.run(schedule, verbose=False)

        assert 'total_energy_in_kWh' in results
        assert 'total_energy_out_kWh' in results
        assert 'round_trip_efficiency' in results

    def test_energy_balance(self):
        """Test energy conservation"""
        cfg = PlantConfig()
        sim = LAESSimulator(cfg)
        schedule = [('charge', 8), ('discharge', 4)]
        results = sim.run(schedule, verbose=False)

        # Energy out should be less than energy in (RTE < 100%)
        assert results['total_energy_out_kWh'] < results['total_energy_in_kWh']
        assert results['total_energy_in_kWh'] > 0

    def test_rte_reasonable(self):
        """Test simulated RTE is reasonable"""
        cfg = PlantConfig()
        sim = LAESSimulator(cfg)
        schedule = SCHEDULES['two_day']
        results = sim.run(schedule, verbose=False)

        # RTE should be between 15% and 50%
        assert 0.15 < results['round_trip_efficiency'] < 0.50

    def test_idle_no_energy(self):
        """Test that idle mode doesn't produce/consume energy"""
        cfg = PlantConfig()
        sim = LAESSimulator(cfg)
        schedule = [('idle', 4)]
        results = sim.run(schedule, verbose=False)

        assert results['total_energy_in_kWh'] == 0
        assert results['total_energy_out_kWh'] == 0

    def test_history_recorded(self):
        """Test that simulation history is recorded"""
        cfg = PlantConfig()
        sim = LAESSimulator(cfg)
        schedule = [('charge', 4), ('discharge', 2)]
        sim.run(schedule, dt_hours=1.0, verbose=False)

        # Should have 6 time steps
        assert len(sim.history) == 6


# ══════════════════════════════════════════════════════════════════════════════
# ECONOMICS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestEconomics:
    """Test economic calculations"""

    def test_capex_positive(self):
        """Test CAPEX is positive"""
        cfg = PlantConfig()
        capex = calculate_capex(cfg)

        assert capex['total'] > 0
        assert capex['per_kW'] > 0
        assert capex['per_kWh'] > 0

    def test_capex_scales_with_power(self):
        """Test CAPEX scales with plant size"""
        cfg_small = PlantConfig(charge_power_MW=10, discharge_power_MW=10)
        cfg_large = PlantConfig(charge_power_MW=50, discharge_power_MW=50)

        capex_small = calculate_capex(cfg_small)['total']
        capex_large = calculate_capex(cfg_large)['total']

        assert capex_large > capex_small

    def test_economics_complete(self):
        """Test economics returns all expected metrics"""
        cfg = PlantConfig()
        econ = calculate_economics(cfg)

        required_keys = [
            'capex_total', 'capex_per_kW', 'capex_per_kWh',
            'annual_opex', 'annual_revenue', 'npv',
            'payback_years', 'lcos_per_MWh'
        ]

        for key in required_keys:
            assert key in econ

    def test_higher_prices_improve_npv(self):
        """Test that higher on-peak prices improve NPV"""
        cfg_low = PlantConfig(price_onpeak_MWh=60)
        cfg_high = PlantConfig(price_onpeak_MWh=150)

        npv_low = calculate_economics(cfg_low)['npv']
        npv_high = calculate_economics(cfg_high)['npv']

        assert npv_high > npv_low

    def test_lcos_positive(self):
        """Test LCOS is positive"""
        cfg = PlantConfig()
        econ = calculate_economics(cfg)
        assert econ['lcos_per_MWh'] > 0


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Integration tests combining multiple components"""

    def test_full_workflow(self):
        """Test complete analysis workflow"""
        # Configure
        cfg = PlantConfig(
            charge_power_MW=10,
            discharge_power_MW=10,
            tank_capacity_tonnes=200,
        )

        # Thermodynamics
        rte_result = calculate_rte(cfg)
        assert rte_result['rte_with_cold'] > 0

        # Simulation
        sim = LAESSimulator(cfg)
        sim_results = sim.run(SCHEDULES['two_day'], verbose=False)
        assert sim_results['round_trip_efficiency'] > 0

        # Economics
        econ = calculate_economics(cfg, rte=rte_result['rte_with_cold'])
        assert 'npv' in econ

    def test_cold_recycle_visible_in_simulation(self):
        """Test that cold storage cycles during two_day schedule"""
        cfg = PlantConfig(tank_capacity_tonnes=500)
        sim = LAESSimulator(cfg)
        sim.run(SCHEDULES['two_day'], verbose=False)

        # Cold storage should have been charged at some point
        assert sim.cold_storage.total_charged_J > 0

        # And discharged
        assert sim.cold_storage.total_discharged_J > 0


# ══════════════════════════════════════════════════════════════════════════════
# RUN TESTS
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
