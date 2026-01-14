"""
LAES Thermodynamics Module
==========================

Core thermodynamic calculations for liquefaction and power recovery cycles.
Uses CoolProp for accurate air properties.

Author: [Your Name]
License: MIT
"""

from typing import Dict, Tuple
from CoolProp.CoolProp import PropsSI

from .config import PlantConfig


def compressor_stage(
    T_in: float, P_in: float, P_out: float, eta_s: float
) -> Tuple[float, float, float]:
    """
    Calculate single compressor stage performance.
    
    Parameters
    ----------
    T_in : float
        Inlet temperature [K]
    P_in : float
        Inlet pressure [Pa]
    P_out : float
        Outlet pressure [Pa]
    eta_s : float
        Isentropic efficiency
    
    Returns
    -------
    T_out : float
        Outlet temperature [K]
    h_out : float
        Outlet specific enthalpy [J/kg]
    w_actual : float
        Specific work input [J/kg]
    
    Notes
    -----
    Governing equations:
        w_isentropic = h_out_s - h_in
        w_actual = w_isentropic / η_s
        h_out = h_in + w_actual
    """
    h_in = PropsSI('H', 'T', T_in, 'P', P_in, 'Air')
    s_in = PropsSI('S', 'T', T_in, 'P', P_in, 'Air')
    
    # Isentropic outlet
    h_out_s = PropsSI('H', 'S', s_in, 'P', P_out, 'Air')
    
    # Actual work
    w_isentropic = h_out_s - h_in
    w_actual = w_isentropic / eta_s
    h_out = h_in + w_actual
    
    # Outlet temperature
    T_out = PropsSI('T', 'H', h_out, 'P', P_out, 'Air')
    
    return T_out, h_out, w_actual


def turbine_stage(
    T_in: float, P_in: float, P_out: float, eta_s: float
) -> Tuple[float, float, float]:
    """
    Calculate single turbine stage performance.
    
    Parameters
    ----------
    T_in : float
        Inlet temperature [K]
    P_in : float
        Inlet pressure [Pa]
    P_out : float
        Outlet pressure [Pa]
    eta_s : float
        Isentropic efficiency
    
    Returns
    -------
    T_out : float
        Outlet temperature [K]
    h_out : float
        Outlet specific enthalpy [J/kg]
    w_actual : float
        Specific work output [J/kg]
    
    Notes
    -----
    Governing equations:
        w_isentropic = h_in - h_out_s
        w_actual = w_isentropic × η_s
        h_out = h_in - w_actual
    """
    h_in = PropsSI('H', 'T', T_in, 'P', P_in, 'Air')
    s_in = PropsSI('S', 'T', T_in, 'P', P_in, 'Air')
    
    # Isentropic outlet
    h_out_s = PropsSI('H', 'S', s_in, 'P', P_out, 'Air')
    
    # Actual work
    w_isentropic = h_in - h_out_s
    w_actual = w_isentropic * eta_s
    h_out = h_in - w_actual
    
    # Outlet temperature
    T_out = PropsSI('T', 'H', h_out, 'P', P_out, 'Air')
    
    return T_out, h_out, w_actual


def calculate_liquefaction(cfg: PlantConfig, cold_available_J_per_kg: float = 0) -> Dict:
    """
    Calculate liquefaction cycle (Claude cycle) performance.
    
    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    cold_available_J_per_kg : float, optional
        Cold energy available from storage [J/kg air processed]
    
    Returns
    -------
    dict
        Performance metrics including:
        - liquid_yield: Fraction of inlet air liquefied
        - specific_consumption_J_per_kg: Energy per kg liquid [J/kg]
        - specific_consumption_kWh_per_kg: Energy per kg liquid [kWh/kg]
        - heat_rejected_J_per_kg: Intercooler heat rejection [J/kg]
        - cold_used_J_per_kg: Cold energy used [J/kg]
    
    Notes
    -----
    Claude cycle:
    1. Multi-stage compression with intercooling
    2. Heat exchange with return gas
    3. Cold storage heat exchange (if available)
    4. Flow split: bypass through turbine
    5. J-T expansion of main stream
    6. Phase separation
    """
    P_high = cfg.P_charge_Pa
    P_low = cfg.P_ambient_Pa
    T_ambient = cfg.T_ambient_K
    T_intercool = cfg.T_intercool_K
    
    # Multi-stage compression with intercooling
    n_stages = cfg.n_compressor_stages
    pr_stage = (P_high / P_low) ** (1.0 / n_stages)
    
    w_compression = 0
    q_rejected = 0
    T_current = T_ambient
    P_current = P_low
    
    for _ in range(n_stages):
        P_next = P_current * pr_stage
        T_after, h_after, w_stage = compressor_stage(
            T_current, P_current, P_next, cfg.eta_compressor
        )
        w_compression += w_stage
        
        # Intercool to fixed temperature
        h_cooled = PropsSI('H', 'T', T_intercool, 'P', P_next, 'Air')
        q_rejected += h_after - h_cooled
        
        T_current = T_intercool
        P_current = P_next
    
    # Heat exchanger (cooled by return gas)
    T_cold_return = 200  # K estimate
    T_after_hx1 = T_current - cfg.hx_effectiveness * (T_current - T_cold_return)
    
    # Cold storage heat exchanger
    if cold_available_J_per_kg > 0:
        h_before = PropsSI('H', 'T', T_after_hx1, 'P', P_high, 'Air')
        h_after = h_before - cold_available_J_per_kg
        
        # Don't cool below safe minimum
        T_min_safe = 105  # K
        h_min = PropsSI('H', 'T', T_min_safe, 'P', P_high, 'Air')
        h_after = max(h_after, h_min)
        
        T_after_cold = PropsSI('T', 'H', h_after, 'P', P_high, 'Air')
        cold_used = h_before - h_after
    else:
        T_after_cold = T_after_hx1
        cold_used = 0
    
    # Flow split (Claude cycle)
    bypass_frac = cfg.bypass_fraction
    main_frac = 1 - bypass_frac
    
    # Bypass turbine
    T_bypass_out, _, w_turb = turbine_stage(
        T_after_cold, P_high, P_low, cfg.eta_cryo_turbine
    )
    w_turbine_total = w_turb * bypass_frac
    
    # Second heat exchanger
    T_after_hx2 = T_after_cold - cfg.hx_effectiveness * (T_after_cold - T_bypass_out)
    
    # J-T expansion
    h_before_jt = PropsSI('H', 'T', T_after_hx2, 'P', P_high, 'Air')
    try:
        quality = PropsSI('Q', 'P', P_low, 'H', h_before_jt, 'Air')
        if 0 <= quality <= 1:
            liquid_fraction_jt = 1 - quality
        else:
            liquid_fraction_jt = 0.0
    except:
        liquid_fraction_jt = 0.3  # Fallback estimate
    
    # Overall liquid yield
    liquid_yield = main_frac * liquid_fraction_jt
    
    # Net work and specific consumption
    net_work = w_compression - w_turbine_total
    specific_consumption = net_work / liquid_yield if liquid_yield > 0 else float('inf')
    
    return {
        'liquid_yield': liquid_yield,
        'net_work_J_per_kg': net_work,
        'specific_consumption_J_per_kg': specific_consumption,
        'specific_consumption_kWh_per_kg': specific_consumption / 3.6e6,
        'compression_work_J_per_kg': w_compression,
        'turbine_work_J_per_kg': w_turbine_total,
        'heat_rejected_J_per_kg': q_rejected,
        'cold_used_J_per_kg': cold_used,
        'T_before_JT_K': T_after_hx2,
    }


def calculate_discharge(cfg: PlantConfig) -> Dict:
    """
    Calculate discharge (power recovery) cycle performance.
    
    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    
    Returns
    -------
    dict
        Performance metrics including:
        - net_work_J_per_kg: Net work output [J/kg liquid]
        - net_work_kWh_per_kg: Net work output [kWh/kg liquid]
        - heat_consumed_J_per_kg: Heat input required [J/kg]
        - cold_recoverable_J_per_kg: Cold available for recycle [J/kg]
    
    Notes
    -----
    Power recovery cycle:
    1. Cryogenic pump to high pressure
    2. Cold recovery (stored for next liquefaction)
    3. Evaporation and superheating (using stored heat)
    4. Multi-stage turbine expansion with reheat
    """
    P_high = cfg.P_discharge_Pa
    P_low = cfg.P_ambient_Pa
    T_superheat = cfg.T_superheat_K
    
    # Liquid air state
    T_liquid = PropsSI('T', 'P', P_low, 'Q', 0, 'Air')
    h_liquid = PropsSI('H', 'P', P_low, 'Q', 0, 'Air')
    
    # Cryogenic pump
    rho = PropsSI('D', 'T', T_liquid, 'P', P_low, 'Air')
    v = 1 / rho
    w_pump = v * (P_high - P_low) / cfg.eta_pump
    h_after_pump = h_liquid + w_pump
    T_after_pump = PropsSI('T', 'H', h_after_pump, 'P', P_high, 'Air')
    
    # Cold recovery (as liquid warms to ~-50°C)
    T_cold_end = 223.15  # -50°C
    h_cold_end = PropsSI('H', 'T', T_cold_end, 'P', P_high, 'Air')
    cold_recoverable = h_cold_end - h_after_pump
    
    # Evaporation + superheating
    h_superheat = PropsSI('H', 'T', T_superheat, 'P', P_high, 'Air')
    q_heat_input = h_superheat - h_after_pump
    
    # Multi-stage turbine with reheat
    n_stages = cfg.n_turbine_stages
    pr_stage = (P_high / P_low) ** (1.0 / n_stages)
    
    w_turbine_total = 0
    q_reheat_total = q_heat_input
    T_current = T_superheat
    P_current = P_high
    
    for i in range(n_stages):
        P_next = P_current / pr_stage
        T_out, h_out, w_stage = turbine_stage(
            T_current, P_current, P_next, cfg.eta_turbine
        )
        w_turbine_total += w_stage
        
        # Reheat (except last stage)
        if i < n_stages - 1:
            h_reheat = PropsSI('H', 'T', T_superheat, 'P', P_next, 'Air')
            q_reheat_total += h_reheat - h_out
            T_current = T_superheat
        
        P_current = P_next
    
    w_net = w_turbine_total - w_pump
    
    return {
        'net_work_J_per_kg': w_net,
        'net_work_kWh_per_kg': w_net / 3.6e6,
        'turbine_work_J_per_kg': w_turbine_total,
        'pump_work_J_per_kg': w_pump,
        'heat_consumed_J_per_kg': q_reheat_total,
        'cold_recoverable_J_per_kg': cold_recoverable,
    }


def calculate_rte(cfg: PlantConfig, verbose: bool = False) -> Dict:
    """
    Calculate round-trip efficiency with and without cold recycle.
    
    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    verbose : bool, optional
        Print detailed results
    
    Returns
    -------
    dict
        Results including:
        - rte_no_cold: RTE without cold recycle
        - rte_with_cold: RTE with cold recycle
        - improvement_pct: Percentage improvement from cold recycle
        - liquefaction_no_cold: Liquefaction results without cold
        - liquefaction_with_cold: Liquefaction results with cold
        - discharge: Discharge cycle results
    
    Notes
    -----
    Round-trip efficiency:
        RTE = Energy_out / Energy_in
            = w_discharge / specific_consumption_liquefaction
    """
    # Without cold recycle
    liq_no_cold = calculate_liquefaction(cfg, cold_available_J_per_kg=0)
    dis_result = calculate_discharge(cfg)
    
    rte_no_cold = dis_result['net_work_J_per_kg'] / liq_no_cold['specific_consumption_J_per_kg']
    
    # With cold recycle
    cold_available = dis_result['cold_recoverable_J_per_kg'] * cfg.cold_storage_efficiency
    liq_with_cold = calculate_liquefaction(cfg, cold_available_J_per_kg=cold_available)
    rte_with_cold = dis_result['net_work_J_per_kg'] / liq_with_cold['specific_consumption_J_per_kg']
    
    improvement_pct = (rte_with_cold / rte_no_cold - 1) * 100
    
    if verbose:
        print(f"\n{'═'*60}")
        print(f" ROUND-TRIP EFFICIENCY")
        print(f"{'═'*60}")
        print(f" Without cold recycle: {rte_no_cold:.1%}")
        print(f" With cold recycle:    {rte_with_cold:.1%}")
        print(f" Improvement:          {improvement_pct:+.1f}%")
    
    return {
        'rte_no_cold': rte_no_cold,
        'rte_with_cold': rte_with_cold,
        'improvement_pct': improvement_pct,
        'liquefaction_no_cold': liq_no_cold,
        'liquefaction_with_cold': liq_with_cold,
        'discharge': dis_result,
    }
