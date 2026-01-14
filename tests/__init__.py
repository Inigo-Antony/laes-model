"""
LAES - Liquid Air Energy Storage Model
======================================

A first-principles thermodynamic and economic model for LAES systems.

Quick Start
-----------
>>> from laes import PlantConfig, LAESSimulator, calculate_rte, calculate_economics
>>>
>>> # Create configuration
>>> config = PlantConfig(charge_power_MW=10, discharge_power_MW=10)
>>>
>>> # Calculate thermodynamic performance
>>> rte_result = calculate_rte(config, verbose=True)
>>>
>>> # Run transient simulation
>>> sim = LAESSimulator(config)
>>> results = sim.run([('charge', 8), ('idle', 4), ('discharge', 6)])
>>> sim.plot_results('simulation.png')
>>>
>>> # Economic analysis
>>> econ = calculate_economics(config, rte_result['rte_with_cold'])

Command Line Usage
------------------
    python -m laes --power 10 --hours 4 --schedule two_day

Modules
-------
config
    Configuration dataclass and constants
thermodynamics
    Cycle calculations (liquefaction, discharge, RTE)
storage
    Tank and thermal storage models
simulation
    Transient simulator with plotting
economics
    Financial analysis (CAPEX, NPV, LCOS)
cli
    Command-line interface

Author: [Your Name]
License: MIT
"""

__version__ = "1.0.0"
__author__ = "[Your Name]"

# Configuration
from .config import (
    PlantConfig,
    SCHEDULES,
    SECONDS_PER_HOUR,
    HOURS_PER_DAY,
    HOURS_PER_YEAR,
    T_LIQUID_AIR_K,
    RHO_LIQUID_AIR,
)

# Thermodynamics
from .thermodynamics import (
    calculate_liquefaction,
    calculate_discharge,
    calculate_rte,
    compressor_stage,
    turbine_stage,
)

# Storage
from .storage import (
    ThermalStorage,
    LiquidAirTank,
)

# Simulation
from .simulation import (
    LAESSimulator,
    TimeStepData,
)

# Economics
from .economics import (
    calculate_capex,
    calculate_annual_cashflow,
    calculate_economics,
)

# Define public API
__all__ = [
    # Version
    '__version__',
    '__author__',
    # Config
    'PlantConfig',
    'SCHEDULES',
    'SECONDS_PER_HOUR',
    'HOURS_PER_DAY',
    'HOURS_PER_YEAR',
    'T_LIQUID_AIR_K',
    'RHO_LIQUID_AIR',
    # Thermodynamics
    'calculate_liquefaction',
    'calculate_discharge',
    'calculate_rte',
    'compressor_stage',
    'turbine_stage',
    # Storage
    'ThermalStorage',
    'LiquidAirTank',
    # Simulation
    'LAESSimulator',
    'TimeStepData',
    # Economics
    'calculate_capex',
    'calculate_annual_cashflow',
    'calculate_economics',
]
