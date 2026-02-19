"""
LAES Thermodynamics Module
==========================

Core thermodynamic calculations for liquefaction and power recovery cycles.
Uses CoolProp for accurate air property lookups.

Cycle overview
--------------
Charge (liquefaction)  — Claude cycle:
    Multi-stage compression → intercooling → HX1 (cold return gas pre-cools
    high-pressure air) → optional cold-store HX → flow split → bypass turbine
    + J-T expansion → phase separator → liquid air to tank

Discharge (power recovery) — direct expansion:
    Cryogenic pump → cold recovery (to HGCS) → evaporation + superheating
    (waste compression heat) → multi-stage turbine with inter-stage reheat

Key assumptions are documented inline and in ASSUMPTIONS.md.

Author: Inigo Antony
License: MIT
"""

import warnings
from typing import Dict, Tuple
from CoolProp.CoolProp import PropsSI

from .config import PlantConfig


def compressor_stage(
    T_in: float, P_in: float, P_out: float, eta_s: float
) -> Tuple[float, float, float]:
    """
    Single compressor stage — isentropic model with real-gas properties.

    Parameters
    ----------
    T_in  : float  — Inlet temperature [K]
    P_in  : float  — Inlet pressure [Pa]
    P_out : float  — Outlet pressure [Pa]
    eta_s : float  — Isentropic efficiency [-]

    Returns
    -------
    T_out     : float — Outlet temperature [K]
    h_out     : float — Outlet specific enthalpy [J/kg]
    w_actual  : float — Specific work input [J/kg]  (positive = work in)

    Notes
    -----
    w_actual = (h_out_s - h_in) / η_s
    h_out    = h_in + w_actual
    """
    h_in  = PropsSI('H', 'T', T_in, 'P', P_in,  'Air')
    s_in  = PropsSI('S', 'T', T_in, 'P', P_in,  'Air')
    h_out_s = PropsSI('H', 'S', s_in, 'P', P_out, 'Air')

    w_actual = (h_out_s - h_in) / eta_s
    h_out    = h_in + w_actual
    T_out    = PropsSI('T', 'H', h_out, 'P', P_out, 'Air')

    return T_out, h_out, w_actual


def turbine_stage(
    T_in: float, P_in: float, P_out: float, eta_s: float
) -> Tuple[float, float, float]:
    """
    Single turbine stage — isentropic model with real-gas properties.

    Parameters
    ----------
    T_in  : float  — Inlet temperature [K]
    P_in  : float  — Inlet pressure [Pa]
    P_out : float  — Outlet pressure [Pa]
    eta_s : float  — Isentropic efficiency [-]

    Returns
    -------
    T_out     : float — Outlet temperature [K]
    h_out     : float — Outlet specific enthalpy [J/kg]
    w_actual  : float — Specific work output [J/kg]  (positive = work out)

    Notes
    -----
    w_actual = (h_in - h_out_s) × η_s
    h_out    = h_in − w_actual
    """
    h_in  = PropsSI('H', 'T', T_in, 'P', P_in,  'Air')
    s_in  = PropsSI('S', 'T', T_in, 'P', P_in,  'Air')
    h_out_s = PropsSI('H', 'S', s_in, 'P', P_out, 'Air')

    w_actual = (h_in - h_out_s) * eta_s
    h_out    = h_in - w_actual
    T_out    = PropsSI('T', 'H', h_out, 'P', P_out, 'Air')

    return T_out, h_out, w_actual


def _derive_cold_return_temperature(
    P_high: float,
    P_low: float,
    T_intercool: float,
    bypass_frac: float,
    eta_cryo_turbine: float,
) -> float:
    """
    Physically derived temperature of the cold return stream entering HX1.

    The return stream is a mixture of:
      (a) Bypass turbine exhaust  — mass fraction = bypass_frac
      (b) Phase separator vapour  — mass fraction ≈ main_frac × (1 − Y_approx)

    where Y_approx = 0.30 is a first-pass liquid yield estimate used only for
    the flow-split mass balance (not for the main liquid yield calculation).

    The bypass turbine inlet is estimated at T_intercool — the temperature
    after the last intercooler stage, BEFORE HX1 cools the stream further.
    This is an upper-bound estimate: the true bypass inlet would be cooler
    because HX1 pre-cools it. The result is a slightly conservative
    (too warm) T_cold_return, producing a slightly lower HX1 effectiveness
    than a rigorous iterative calculation. A fully converged value requires
    iteration; see ASSUMPTIONS.md §2.

    Returns
    -------
    T_cold_return : float — Effective cold-return temperature to HX1 [K]
    """
    # (a) Bypass turbine exhaust
    #     Expand from T_intercool (first-pass upper bound on bypass inlet T)
    _, h_bypass_out, _ = turbine_stage(
        T_intercool, P_high, P_low, eta_cryo_turbine
    )

    # (b) Phase separator saturated vapour
    T_sep_vapor = PropsSI('T', 'P', P_low, 'Q', 1, 'Air')   # ≈ 78.9 K
    h_sep_vapor = PropsSI('H', 'T', T_sep_vapor, 'P', P_low, 'Air')

    # Flow fractions
    main_frac = 1.0 - bypass_frac
    Y_approx  = 0.30                              # nominal liquid yield for mass balance only
    vapor_return_frac = main_frac * (1.0 - Y_approx)
    total_return = bypass_frac + vapor_return_frac

    # Mass-enthalpy weighted mixture
    h_return = (
        bypass_frac       * h_bypass_out +
        vapor_return_frac * h_sep_vapor
    ) / total_return

    T_cold_return = PropsSI('T', 'H', h_return, 'P', P_low, 'Air')
    return T_cold_return


def calculate_liquefaction(cfg: PlantConfig, cold_available_J_per_kg: float = 0) -> Dict:
    """
    Liquefaction cycle (Claude cycle) performance.

    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration
    cold_available_J_per_kg : float, optional
        Cold energy recovered from HGCS [J/kg compressed air].
        Applied in the cold-store heat exchanger before the J-T expansion.

    Returns
    -------
    dict with keys:
        liquid_yield              — Fraction of inlet air liquefied [-]
        specific_consumption_*    — Energy per kg liquid [J/kg and kWh/kg]
        heat_rejected_J_per_kg    — Total intercooler heat rejection [J/kg]
        cold_used_J_per_kg        — Cold energy actually extracted from HGCS [J/kg]
        T_before_JT_K             — Temperature entering J-T valve [K]
        T_cold_return_K           — Derived cold return temperature to HX1 [K]

    Notes
    -----
    Claude cycle steps (per unit mass of air at compressor inlet):

        1. 3-stage compression with intercooling to T_intercool (35 °C)
        2. HX1: high-pressure air pre-cooled by cold return stream
           — T_cold_return derived from bypass exhaust + separator vapour
        3. Cold-store HX: further pre-cooling using HGCS cold (if available)
        4. Flow split:
             bypass_frac  → cryogenic turbine → cold gas → recycles to HX1
             (1-bypass_frac) → HX2 → J-T valve → phase separator
        5. Liquid fraction stored; vapour fraction returns through HX1
    """
    P_high     = cfg.P_charge_Pa
    P_low      = cfg.P_ambient_Pa
    T_ambient  = cfg.T_ambient_K
    T_intercool = cfg.T_intercool_K

    # ── 1. Multi-stage compression with intercooling ──────────────────────
    n_stages = cfg.n_compressor_stages
    pr_stage = (P_high / P_low) ** (1.0 / n_stages)

    w_compression = 0.0
    q_rejected    = 0.0
    T_current     = T_ambient
    P_current     = P_low

    for _ in range(n_stages):
        P_next = P_current * pr_stage
        T_after, h_after, w_stage = compressor_stage(
            T_current, P_current, P_next, cfg.eta_compressor
        )
        w_compression += w_stage

        # Intercool to fixed temperature (35 °C)
        h_cooled  = PropsSI('H', 'T', T_intercool, 'P', P_next, 'Air')
        q_rejected += h_after - h_cooled

        T_current = T_intercool
        P_current = P_next
    # T_current = T_intercool, P_current = P_high after the loop

    # ── 2. HX1: pre-cool with cold return gas (physically derived T) ──────
    #
    # T_cold_return is derived from the mass-enthalpy weighted mix of:
    #   - bypass turbine exhaust (expanded from T_intercool as first-pass estimate)
    #   - phase separator saturated vapour (~78.9 K)
    # See _derive_cold_return_temperature() docstring for full justification.
    # A rigorous value requires iteration; a future version will converge this.
    #
    T_cold_return = _derive_cold_return_temperature(
        P_high, P_low, T_intercool,
        cfg.bypass_fraction, cfg.eta_cryo_turbine
    )

    T_after_hx1 = T_current - cfg.hx_effectiveness * (T_current - T_cold_return)

    # ── 3. Cold-store HX: optional pre-cooling from HGCS ──────────────────
    if cold_available_J_per_kg > 0:
        h_before_cold = PropsSI('H', 'T', T_after_hx1, 'P', P_high, 'Air')
        h_after_cold  = h_before_cold - cold_available_J_per_kg

        # Physical lower bound: do not cool below saturation temperature at P_high
        T_min_safe = PropsSI('T', 'P', P_high, 'Q', 0, 'Air') + 2.0   # 2 K margin
        h_min = PropsSI('H', 'T', T_min_safe, 'P', P_high, 'Air')
        h_after_cold = max(h_after_cold, h_min)

        T_after_cold = PropsSI('T', 'H', h_after_cold, 'P', P_high, 'Air')
        cold_used    = h_before_cold - h_after_cold
    else:
        T_after_cold = T_after_hx1
        cold_used    = 0.0

    # ── 4. Flow split ──────────────────────────────────────────────────────
    bypass_frac = cfg.bypass_fraction
    main_frac   = 1.0 - bypass_frac

    # Bypass turbine (cryogenic expander)
    T_bypass_out, _, w_turb = turbine_stage(
        T_after_cold, P_high, P_low, cfg.eta_cryo_turbine
    )
    w_turbine_total = w_turb * bypass_frac

    # HX2: main stream further cooled by bypass exhaust
    T_after_hx2 = T_after_cold - cfg.hx_effectiveness * (T_after_cold - T_bypass_out)

    # ── 5. J-T expansion → phase separator ────────────────────────────────
    h_before_jt = PropsSI('H', 'T', T_after_hx2, 'P', P_high, 'Air')
    try:
        quality = PropsSI('Q', 'P', P_low, 'H', h_before_jt, 'Air')
        if 0.0 <= quality <= 1.0:
            liquid_fraction_jt = 1.0 - quality
        else:
            # Operating point is outside the two-phase dome (superheated or subcooled)
            liquid_fraction_jt = 0.0
            if quality > 1.0:
                warnings.warn(
                    f"J-T expansion produced superheated vapour (quality={quality:.3f}). "
                    "No liquid yield from main stream. Check charge pressure and T_before_JT.",
                    UserWarning,
                    stacklevel=2,
                )
    except Exception as exc:
        liquid_fraction_jt = 0.0
        warnings.warn(
            f"CoolProp could not compute J-T quality at P={P_low:.0f} Pa, "
            f"h={h_before_jt:.0f} J/kg: {exc}. Liquid yield set to 0. "
            "Operating point may be supercritical — reduce T_before_JT or increase P_charge.",
            UserWarning,
            stacklevel=2,
        )

    # Overall liquid yield (fraction of inlet air that ends as stored liquid)
    liquid_yield = main_frac * liquid_fraction_jt

    # Net specific work and specific consumption per kg of liquid produced
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
        'T_cold_return_K': T_cold_return,
    }


def calculate_discharge(cfg: PlantConfig) -> Dict:
    """
    Discharge (power recovery) cycle performance.

    Parameters
    ----------
    cfg : PlantConfig
        Plant configuration

    Returns
    -------
    dict with keys:
        net_work_J_per_kg         — Net work output [J/kg liquid air]
        net_work_kWh_per_kg       — Net work output [kWh/kg liquid air]
        heat_consumed_J_per_kg    — Total heat input (compression waste heat) [J/kg]
        cold_recoverable_J_per_kg — Cold available for HGCS storage [J/kg]
        pump_work_J_per_kg        — Cryogenic pump work [J/kg]
        turbine_work_J_per_kg     — Total turbine work [J/kg]

    Notes
    -----
    Power recovery cycle steps (per kg of liquid air from tank):

        1. Cryogenic pump: raise pressure from P_ambient to P_discharge
           — incompressible liquid work: w_pump = v·ΔP / η_pump
        2. Cold recovery: liquid warms from pump outlet to T_intercool
           — enthalpy difference stored in HGCS for next charge cycle
           — upper bound T = T_intercool (308.15 K), the compressor
             inlet reference temperature; cold above this cannot help
             the liquefaction pre-cooling
        3. Evaporation + superheating to T_superheat using stored
           compression heat (HGWS); no external heat source assumed
        4. n_turbine_stages expansion stages, each with inter-stage
           reheat back to T_superheat
    """
    P_high     = cfg.P_discharge_Pa
    P_low      = cfg.P_ambient_Pa
    T_superheat = cfg.T_superheat_K

    # ── 1. Cryogenic pump (incompressible liquid work) ────────────────────
    T_liquid = PropsSI('T', 'P', P_low, 'Q', 0, 'Air')     # ≈ 78.9 K
    h_liquid = PropsSI('H', 'P', P_low, 'Q', 0, 'Air')

    rho_liquid = PropsSI('D', 'T', T_liquid, 'P', P_low, 'Air')
    v_liquid   = 1.0 / rho_liquid
    w_pump     = v_liquid * (P_high - P_low) / cfg.eta_pump
    h_after_pump = h_liquid + w_pump
    T_after_pump = PropsSI('T', 'H', h_after_pump, 'P', P_high, 'Air')

    # ── 2. Cold recovery ──────────────────────────────────────────────────
    #
    # The HGCS stores cold from the pump outlet temperature up to T_intercool.
    # Physical upper bound:
    #   Cold above T_intercool cannot usefully pre-cool the high-pressure
    #   air in the liquefaction cold box (the compressor recycles to T_intercool).
    #   T_intercool (308.15 K) is therefore the maximum recovery temperature.
    #
    # The packed-bed HGCS round-trip efficiency (cold_storage_efficiency = 0.85)
    # is applied separately in calculate_rte() when the stored cold is returned.
    # See ASSUMPTIONS.md §5 for HGCS loss discussion.
    #
    T_cold_recovery_end = cfg.T_intercool_K
    h_cold_end = PropsSI('H', 'T', T_cold_recovery_end, 'P', P_high, 'Air')
    cold_recoverable = h_cold_end - h_after_pump    # positive [J/kg]

    # ── 3. Evaporation + superheating ─────────────────────────────────────
    h_superheat  = PropsSI('H', 'T', T_superheat, 'P', P_high, 'Air')
    q_heat_input = h_superheat - h_after_pump       # includes evaporation

    # ── 4. Multi-stage turbine with inter-stage reheat ────────────────────
    n_stages = cfg.n_turbine_stages
    pr_stage = (P_high / P_low) ** (1.0 / n_stages)

    w_turbine_total = 0.0
    q_reheat_total  = q_heat_input      # initial superheat already included
    T_current       = T_superheat
    P_current       = P_high

    for i in range(n_stages):
        P_next = P_current / pr_stage
        T_out, h_out, w_stage = turbine_stage(
            T_current, P_current, P_next, cfg.eta_turbine
        )
        w_turbine_total += w_stage

        # Inter-stage reheat (except after the last stage)
        if i < n_stages - 1:
            h_reheat = PropsSI('H', 'T', T_superheat, 'P', P_next, 'Air')
            q_reheat_total += h_reheat - h_out
            T_current = T_superheat
        else:
            T_current = T_out

        P_current = P_next

    w_net = w_turbine_total - w_pump

    return {
        'net_work_J_per_kg': w_net,
        'net_work_kWh_per_kg': w_net / 3.6e6,
        'turbine_work_J_per_kg': w_turbine_total,
        'pump_work_J_per_kg': w_pump,
        'heat_consumed_J_per_kg': q_reheat_total,
        'cold_recoverable_J_per_kg': cold_recoverable,
        'T_cold_recovery_end_K': T_cold_recovery_end,
    }


def calculate_rte(cfg: PlantConfig, verbose: bool = False) -> Dict:
    """
    Round-trip efficiency with and without cold recycle.

    RTE = net_work_discharge / specific_consumption_liquefaction
        = w_net [J/kg liquid] / SC [J/kg liquid]

    This is dimensionally consistent: both numerator and denominator are
    per kg of liquid air, so kg cancels and the ratio is dimensionless.
    Equivalent to Equation (1) in Borri et al. (2021).

    Parameters
    ----------
    cfg     : PlantConfig
    verbose : bool — print detailed results

    Returns
    -------
    dict with keys:
        rte_no_cold    — RTE without cold recycle [-]
        rte_with_cold  — RTE with cold recycle [-]
        improvement_pct
        liquefaction_no_cold
        liquefaction_with_cold
        discharge
    """
    # Discharge cycle (same regardless of cold recycle)
    dis_result = calculate_discharge(cfg)

    # Case 1: no cold recycle
    liq_no_cold = calculate_liquefaction(cfg, cold_available_J_per_kg=0)
    rte_no_cold = (
        dis_result['net_work_J_per_kg']
        / liq_no_cold['specific_consumption_J_per_kg']
    )

    # Case 2: with cold recycle (HGCS efficiency applied)
    cold_available = (
        dis_result['cold_recoverable_J_per_kg'] * cfg.cold_storage_efficiency
    )
    liq_with_cold = calculate_liquefaction(cfg, cold_available_J_per_kg=cold_available)
    rte_with_cold = (
        dis_result['net_work_J_per_kg']
        / liq_with_cold['specific_consumption_J_per_kg']
    )

    improvement_pct = (rte_with_cold / rte_no_cold - 1) * 100

    if verbose:
        print(f"\n{'╒'*60}")
        print(f" LIQUEFACTION (charge cycle)")
        print(f"{'╒'*60}")
        print(f"   Derived T_cold_return:  {liq_no_cold['T_cold_return_K']:.1f} K "
              f"({liq_no_cold['T_cold_return_K'] - 273.15:.1f} °C)")
        print(f"   T before J-T (no cold): {liq_no_cold['T_before_JT_K']:.1f} K")
        print(f"   T before J-T (w/ cold): {liq_with_cold['T_before_JT_K']:.1f} K")
        print(f"   Liquid yield (no cold): {liq_no_cold['liquid_yield']:.1%}")
        print(f"   Liquid yield (w/ cold): {liq_with_cold['liquid_yield']:.1%}")
        print(f"   SC (no cold): {liq_no_cold['specific_consumption_kWh_per_kg']:.3f} kWh/kg")
        print(f"   SC (w/ cold): {liq_with_cold['specific_consumption_kWh_per_kg']:.3f} kWh/kg")

        print(f"\n{'╒'*60}")
        print(f" DISCHARGE (power recovery cycle)")
        print(f"{'╒'*60}")
        print(f"   Turbine stages:   {cfg.n_turbine_stages}")
        print(f"   Superheat temp:   {cfg.T_superheat_C:.0f} °C")
        print(f"   Net work:         {dis_result['net_work_kWh_per_kg']:.3f} kWh/kg")
        print(f"   Cold recoverable: {dis_result['cold_recoverable_J_per_kg']/1000:.1f} kJ/kg")
        print(f"   Cold recovery end:{dis_result['T_cold_recovery_end_K'] - 273.15:.0f} °C")

        print(f"\n{'╒'*60}")
        print(f" ROUND-TRIP EFFICIENCY")
        print(f"{'╒'*60}")
        print(f"   Without cold recycle: {rte_no_cold:.1%}")
        print(f"   With cold recycle:    {rte_with_cold:.1%}")
        print(f"   Improvement:          {improvement_pct:+.1f}%")

    return {
        'rte_no_cold': rte_no_cold,
        'rte_with_cold': rte_with_cold,
        'improvement_pct': improvement_pct,
        'liquefaction_no_cold': liq_no_cold,
        'liquefaction_with_cold': liq_with_cold,
        'discharge': dis_result,
    }
