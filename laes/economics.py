"""
LAES Economics Module
=====================

Economic analysis including CAPEX, OPEX, revenue, and financial metrics.

Author: [Your Name]
License: MIT
"""

from typing import Dict
from .config import PlantConfig, RHO_LIQUID_AIR
from .thermodynamics import calculate_rte


def calculate_capex(cfg: PlantConfig, verbose: bool = False) -> Dict:
    """
    Calculate capital costs.
    
    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    verbose : bool
        Print detailed breakdown
    
    Returns
    -------
    dict
        Itemized costs and totals
    
    Notes
    -----
    Cost basis (parametric estimates):
    - Compressor: $500/kW input
    - Turbine: $400/kW output
    - Heat exchangers: $75/kW thermal
    - Cryogenic tank: $800/m³
    - Hot storage: $30/kWh thermal
    - Cold storage: $45/kWh thermal
    - BOP: 20% of equipment
    - Installation: 25% of equipment
    
    Uncertainty: ±30-50%
    """
    # Get thermodynamic results for sizing
    rte_result = calculate_rte(cfg, verbose=False)
    
    # Sizing
    heat_per_kg = rte_result['discharge']['heat_consumed_J_per_kg']
    cold_per_kg = rte_result['discharge']['cold_recoverable_J_per_kg']
    
    tank_m3 = cfg.tank_capacity_kg / RHO_LIQUID_AIR
    hot_storage_kWh = cfg.tank_capacity_kg * heat_per_kg / 3.6e6
    cold_storage_kWh = cfg.tank_capacity_kg * cold_per_kg / 3.6e6
    
    # Component costs
    compressor = 500 * cfg.charge_power_kW
    turbine = 400 * cfg.discharge_power_kW
    cryo_tank = 800 * tank_m3
    hot_storage = 30 * hot_storage_kWh
    cold_storage = 45 * cold_storage_kWh
    hx = 75 * hot_storage_kWh / cfg.storage_duration_hours
    
    equipment = compressor + turbine + cryo_tank + hot_storage + cold_storage + hx
    bop = equipment * 0.20
    installation = equipment * 0.25
    total = equipment + bop + installation
    
    # Per-unit costs
    per_kW = total / cfg.discharge_power_kW
    per_kWh = total / cfg.storage_capacity_MWh / 1000
    
    result = {
        'compressor': compressor,
        'turbine': turbine,
        'cryo_tank': cryo_tank,
        'hot_storage': hot_storage,
        'cold_storage': cold_storage,
        'heat_exchangers': hx,
        'equipment_total': equipment,
        'bop': bop,
        'installation': installation,
        'total': total,
        'per_kW': per_kW,
        'per_kWh': per_kWh,
    }
    
    if verbose:
        print(f"\n{'═'*60}")
        print(f" CAPITAL COSTS (CAPEX)")
        print(f"{'═'*60}")
        print(f"\n Component Costs:")
        print(f"   Compressor:       ${compressor:>12,.0f}")
        print(f"   Turbine:          ${turbine:>12,.0f}")
        print(f"   Cryogenic Tank:   ${cryo_tank:>12,.0f}")
        print(f"   Hot Storage:      ${hot_storage:>12,.0f}")
        print(f"   Cold Storage:     ${cold_storage:>12,.0f}")
        print(f"   Heat Exchangers:  ${hx:>12,.0f}")
        print(f"   {'─'*40}")
        print(f"   Equipment Total:  ${equipment:>12,.0f}")
        print(f"\n Indirect Costs:")
        print(f"   Balance of Plant: ${bop:>12,.0f}")
        print(f"   Installation:     ${installation:>12,.0f}")
        print(f"   {'─'*40}")
        print(f"   TOTAL CAPEX:      ${total:>12,.0f}")
        print(f"\n Unit Costs:")
        print(f"   Per kW discharge: ${per_kW:>12,.0f}")
        print(f"   Per kWh storage:  ${per_kWh:>12,.0f}")
    
    return result


def calculate_annual_cashflow(
    cfg: PlantConfig,
    capex: Dict,
    rte: float,
    cycles_per_year: int = 365,
    verbose: bool = False
) -> Dict:
    """
    Calculate annual operating costs and revenue.
    
    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    capex : dict
        Capital costs from calculate_capex()
    rte : float
        Round-trip efficiency
    cycles_per_year : int
        Operating cycles per year
    verbose : bool
        Print breakdown
    
    Returns
    -------
    dict
        Annual costs, revenue, and net cash flow
    """
    # Operating costs
    maintenance = capex['total'] * 0.015  # 1.5% of CAPEX
    insurance = capex['total'] * 0.005    # 0.5% of CAPEX
    
    # Energy flows
    energy_in_MWh = cfg.charge_power_MW * cfg.storage_duration_hours * cycles_per_year
    energy_out_MWh = energy_in_MWh * rte
    
    electricity_cost = energy_in_MWh * cfg.price_offpeak_MWh
    
    total_opex = maintenance + insurance + electricity_cost
    
    # Revenue
    energy_revenue = energy_out_MWh * cfg.price_onpeak_MWh
    capacity_revenue = cfg.discharge_power_kW * 50  # $50/kW-year
    
    total_revenue = energy_revenue + capacity_revenue
    net_cf = total_revenue - total_opex
    
    result = {
        'maintenance': maintenance,
        'insurance': insurance,
        'electricity_cost': electricity_cost,
        'total_opex': total_opex,
        'energy_revenue': energy_revenue,
        'capacity_revenue': capacity_revenue,
        'total_revenue': total_revenue,
        'net_cash_flow': net_cf,
        'energy_in_MWh': energy_in_MWh,
        'energy_out_MWh': energy_out_MWh,
    }
    
    if verbose:
        print(f"\n{'═'*60}")
        print(f" ANNUAL CASH FLOW")
        print(f"{'═'*60}")
        print(f"\n Operating Costs:")
        print(f"   Maintenance:   ${maintenance:>12,.0f}")
        print(f"   Insurance:     ${insurance:>12,.0f}")
        print(f"   Electricity:   ${electricity_cost:>12,.0f}")
        print(f"   {'─'*35}")
        print(f"   Total OPEX:    ${total_opex:>12,.0f}")
        print(f"\n Revenue:")
        print(f"   Energy Sales:  ${energy_revenue:>12,.0f}")
        print(f"   Capacity:      ${capacity_revenue:>12,.0f}")
        print(f"   {'─'*35}")
        print(f"   Total Revenue: ${total_revenue:>12,.0f}")
        print(f"\n Net Cash Flow:   ${net_cf:>12,.0f}")
    
    return result


def calculate_economics(
    cfg: PlantConfig,
    rte: float = None,
    verbose: bool = False
) -> Dict:
    """
    Calculate complete economic analysis.
    
    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    rte : float, optional
        Round-trip efficiency (calculated if not provided)
    verbose : bool
        Print detailed results
    
    Returns
    -------
    dict
        Financial metrics including:
        - capex_total: Total capital cost [$]
        - annual_opex: Annual operating cost [$]
        - annual_revenue: Annual revenue [$]
        - npv: Net present value [$]
        - payback_years: Simple payback period [years]
        - lcos_per_MWh: Levelized cost of storage [$/MWh]
    """
    # Get RTE if not provided
    if rte is None:
        rte_result = calculate_rte(cfg, verbose=False)
        rte = rte_result['rte_with_cold']
    
    # CAPEX and cash flow
    capex = calculate_capex(cfg, verbose=verbose)
    cashflow = calculate_annual_cashflow(cfg, capex, rte, verbose=verbose)
    
    # Financial metrics
    r = cfg.discount_rate
    n = cfg.project_years
    
    # Capital recovery factor
    crf = r * (1 + r)**n / ((1 + r)**n - 1)
    
    # NPV
    npv = -capex['total']
    for year in range(1, n + 1):
        degradation = 0.995 ** year  # 0.5% per year
        year_cf = cashflow['net_cash_flow'] * degradation
        npv += year_cf / (1 + r) ** year
    
    # Payback
    payback = (
        capex['total'] / cashflow['net_cash_flow']
        if cashflow['net_cash_flow'] > 0 else float('inf')
    )
    
    # LCOS
    annual_capex = capex['total'] * crf
    total_annual_cost = annual_capex + cashflow['total_opex']
    lcos = (
        total_annual_cost / cashflow['energy_out_MWh']
        if cashflow['energy_out_MWh'] > 0 else float('inf')
    )
    
    result = {
        'capex_total': capex['total'],
        'capex_per_kW': capex['per_kW'],
        'capex_per_kWh': capex['per_kWh'],
        'annual_opex': cashflow['total_opex'],
        'annual_revenue': cashflow['total_revenue'],
        'annual_net_cf': cashflow['net_cash_flow'],
        'npv': npv,
        'payback_years': payback,
        'lcos_per_MWh': lcos,
        'rte': rte,
    }
    
    if verbose:
        print(f"\n{'═'*60}")
        print(f" FINANCIAL METRICS")
        print(f"{'═'*60}")
        print(f"   NPV ({n} years): ${npv:>12,.0f}")
        print(f"   Simple Payback: {payback:>12.1f} years")
        print(f"   LCOS:           ${lcos:>12.0f}/MWh")
    
    return result
