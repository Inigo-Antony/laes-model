# LAES Model — Assumptions & Simplifications

This document explicitly states every assumption embedded in the model. It is intended to help users understand the model's scope, calibrate their trust in its outputs, and identify areas for future improvement.

---

## 1. Working Fluid & Physical Constants

| Parameter | Value | Source / Rationale |
|---|---|---|
| Working fluid | Dry Air (CoolProp `'Air'`) | Simplified pseudo-pure fluid. Real air contains ~78% N₂, ~21% O₂, ~1% Ar. CoolProp's `'Air'` mixture is a reasonable approximation. |
| Ambient pressure | 101,325 Pa (1 atm) | Sea-level standard atmosphere |
| Liquid air boiling point | 78.9 K (−194.25 °C) | Derived from CoolProp at 1 atm. Actual air boils at ≈81 K due to O₂/N₂ composition; CoolProp pseudo-pure slightly underestimates. |
| Liquid air density | 875 kg/m³ | CoolProp value at boiling point, 1 atm. Consistent with published values (870–880 kg/m³). |

---

## 2. Liquefaction Cycle (Charge Phase)

### 2.1 Cycle Type
The model implements a simplified **Claude cycle** with:
- Multi-stage intercooled compression
- Two main heat exchangers (HX1 and HX2)
- One cryogenic bypass turbine
- Joule-Thomson (J-T) expansion valve
- Phase separator

### 2.2 Compression

| Assumption | Value | Notes |
|---|---|---|
| Number of stages | 3 (default) | Configurable via `n_compressor_stages` |
| Pressure ratio per stage | Equal distribution: `(P_high/P_low)^(1/n)` | Optimal equal pressure ratio assumption — valid for minimising work with equal efficiencies |
| Intercooler outlet temperature | 308.15 K (35 °C) | Fixed. Real intercoolers approach ambient temperature; 35 °C is a reasonable industrial target. |
| Compressor isentropic efficiency | 85% | Typical for industrial multi-stage centrifugal compressors. Range: 78–88%. |
| Charge pressure | 50 bar (default) | Configurable. Literature range for LAES: 40–100 bar. Higher pressure improves liquid yield at cost of specific compression work. |

### 2.3 Main Heat Exchanger (HX1) — Key Simplification

> ⚠️ **Critical assumption**: The cold return gas temperature is hardcoded at **200 K** rather than being calculated from a self-consistent energy balance.

```python
T_cold_return = 200  # K — estimate; NOT derived from pinch analysis
T_after_hx1 = T_current - hx_effectiveness × (T_current - T_cold_return)
```

The 200 K approximates the mixed temperature of bypassed turbine outlet gas and vapour from the phase separator. A rigorous model would iterate to find the self-consistent temperature that satisfies the counterflow heat exchanger energy balance. This simplification introduces ~10–15% error in cooling depth and consequently in liquid yield.

| Parameter | Value | Notes |
|---|---|---|
| HX effectiveness | 0.90 | Applies uniformly to all HXs. Real cryogenic plate-fin HXs can achieve 0.92–0.97 approach temperatures. |
| HX model type | Effectiveness-NTU (simplified) | No pinch analysis; no stream matching across temperature levels. |

### 2.4 Cryogenic Bypass Turbine

| Assumption | Value | Notes |
|---|---|---|
| Bypass fraction | 0.60 (default) | 60% of compressed flow diverted through turbine; 40% continues to J-T valve. Literature optimum for Claude cycle: 30–60%. This value is on the high side and was not optimised for maximum liquid yield. |
| Cryoturbine isentropic efficiency | 80% | Conservative. Modern cryogenic turbines achieve 82–90%. |

### 2.5 J-T Expansion

The J-T valve is modelled as isenthalpic (h₄ = h₅), which is thermodynamically exact. Phase quality is computed using CoolProp's two-phase properties. If CoolProp returns an error (supercritical conditions), the model falls back to a **hardcoded 30% liquid fraction** — this fallback is a rough approximation and will be triggered if cycle conditions push the pre-J-T state above the critical point.

### 2.6 Cold Storage Integration

When cold recycle is active:
- Available cold energy per kg = `cold_recoverable_J_per_kg × cold_storage_efficiency`
- Applied as a heat sink on the high-pressure stream between HX1 and HX2
- Minimum pre-J-T temperature clamped at **105 K** to avoid numerical issues
- Cold storage round-trip efficiency: 85%

---

## 3. Discharge / Power Recovery Cycle

### 3.1 Cryogenic Pump

Pump work is calculated assuming **incompressible liquid** at the boiling point:

```
w_pump = (P_high − P_low) / (ρ × η_pump)
```

This is the standard hydraulic work formula for liquids and is thermodynamically appropriate for cryogenic pumps. Pump efficiency: **75%** (typical for small cryogenic reciprocating pumps; large centrifugal cryopumps achieve 80–85%).

### 3.2 Cold Recovery

Cold energy is recovered as the liquid air warms from the pump outlet (≈−194 °C) to **−50 °C** (223.15 K) at high pressure before evaporation. This temperature cutoff is hardcoded:

```python
T_cold_end = 223.15  # K (-50°C) — hardcoded upper bound for cold recovery
```

This assumes that the HGCS captures cold across the full −194 °C to −50 °C range. In practice, the effective cold capture window depends on the HGCS design, packed bed thermocline, and the temperature match with the liquefaction HX. Real cold recovery captures approximately **50–75% of theoretical maximum**.

### 3.3 Evaporation and Superheating

The model assumes the liquid air is fully evaporated and superheated to the turbine inlet temperature using stored compression heat from the charge cycle (HGWS). The model does **not** check whether the stored compression heat is sufficient to reach the target superheat temperature — it assumes perfect thermal coupling.

| Parameter | Value | Notes |
|---|---|---|
| Turbine inlet temperature | 200 °C / 473 K (default) | Configurable. Limited by hot storage fluid properties. Literature typically uses 120–300 °C. |
| Discharge pressure | 70 bar (default) | Configurable. Literature optimum: 60–100 bar. |

### 3.4 Turbine Stages

| Assumption | Value | Notes |
|---|---|---|
| Number of turbine stages | **2** (default) | Configurable via `n_turbine_stages`. Real commercial LAES plants use **4 stages with reheat**. This is the primary reason model RTE (26–28%) is lower than literature (45–62%). |
| Pressure ratio per stage | Equal: `(P_high/P_low)^(1/n)` | Optimal equal distribution |
| Turbine isentropic efficiency | 85% | Reasonable for modern radial turbines |
| Reheat temperature | Same as turbine inlet (200 °C) | Each inter-stage reheat returns to initial superheat temperature using stored heat |

---

## 4. Thermal Storage

### 4.1 Hot Thermal Storage (HGWS)

The HGWS stores compression heat rejected by intercoolers for use as turbine inlet superheat.

| Parameter | Value | Notes |
|---|---|---|
| Round-trip efficiency | 90% | Modelled as symmetric √η on charge and discharge |
| Heat loss rate | 2% / day | Conservative assumption; real insulated thermal oil tanks lose 0.5–1.5%/day |
| Capacity | Sized from tank capacity × specific heat input | Assumes full use at each cycle |

### 4.2 Cold Thermal Storage (HGCS)

The HGCS stores cold energy recovered from liquid air regasification for use in the next liquefaction cycle.

| Parameter | Value | Notes |
|---|---|---|
| Round-trip efficiency | 85% | Accounts for thermocline mixing losses in packed beds. Literature: 75–90% depending on design. |
| Cold loss rate | 5% / day | Accounts for heat ingress to cold storage. This is conservative and higher than the main liquid air tank. |

> **Note**: The Borri et al. (2021) review highlights that cold energy losses affect RTE approximately **7× more** than equivalent heat losses. The HGCS efficiency of 85% is therefore the most sensitive economic and thermodynamic parameter in the model.

---

## 5. Liquid Air Storage Tank

| Parameter | Value | Notes |
|---|---|---|
| Boil-off rate | 0.2% / day | Consistent with literature (0.1–0.2% / day for unpressurised vacuum-insulated cryogenic vessels). |
| Minimum level | 10% of capacity | Maintained for cryo-pump NPSH and to avoid vortexing |
| Storage pressure | Ambient (unpressurised) | Consistent with LAES design philosophy |
| Tank density for volume calculation | 875 kg/m³ | Liquid air at 1 atm, boiling point |

---

## 6. System-Level Assumptions

### 6.1 Steady-State Operation

The thermodynamic cycle calculations (`calculate_liquefaction`, `calculate_discharge`) assume **steady-state, nominal design conditions**. They do not account for:
- Start-up and shutdown transients
- Part-load or variable-load operation
- Thermal cycling effects on components
- Thermocline degradation over repeated HGCS charge/discharge cycles

### 6.2 Perfect Component Coupling

The model assumes:
- All compression heat is perfectly recovered and stored in HGWS with no bypass losses
- All discharge cold is perfectly captured by HGCS
- No parasitic loads (controls, lighting, auxiliary systems) beyond the main thermodynamic cycle

### 6.3 Round-Trip Efficiency Calculation

RTE is computed as:

```
RTE = (net discharge work per kg liquid) / (specific consumption per kg liquid)
    = SP / SC
```

where SP = specific power output [kWh/kg] and SC = specific consumption [kWh/kg]. This is dimensionally and thermodynamically correct.

---

## 7. Economic Assumptions

| Parameter | Value | Basis / Uncertainty |
|---|---|---|
| Compressor cost | $500 / kW input | Parametric estimate. Literature range: $300–800/kW. ±30% |
| Turbine cost | $400 / kW output | Parametric estimate. ±30% |
| Cryogenic tank | $800 / m³ | Parametric estimate for vacuum-insulated vessels. ±40% |
| Hot thermal storage | $30 / kWh thermal | Based on thermal oil tank costs. ±30% |
| Cold thermal storage | $45 / kWh thermal | Higher than hot due to cryogenic insulation. ±40% |
| Heat exchangers | $75 / kW thermal | Plate-fin cryogenic HX estimate. ±35% |
| Balance of Plant (BOP) | 20% of equipment cost | Industry rule of thumb |
| Installation & EPC | 25% of equipment cost | Typical for energy projects |
| O&M | 1.5% of CAPEX / year | Industry norm for mechanical energy storage |
| Insurance | 0.5% of CAPEX / year | Typical |
| Capacity payment | $50 / kW-year | Simplified; actual capacity market rates vary widely by jurisdiction |
| Annual degradation | 0.5% / year | Applied to net cash flow. Conservative for mechanical systems (no cell degradation). |
| Project lifetime | 25 years | Consistent with literature (30–40 years operational lifetime, 25 years for financial model) |
| Discount rate | 8% | Real rate. Adjust for project risk profile. |
| Cycles per year | 365 (1 full cycle/day) | Optimistic; real dispatch may be lower depending on market conditions |

> **Overall CAPEX uncertainty: ±30–50%.** All cost figures are order-of-magnitude estimates suitable for pre-FEED screening only. Detailed costing requires vendor quotes and site-specific data.

---

## 8. What This Model Does NOT Include

The following physically important effects are **not modelled** and represent the primary gaps between model outputs and real-world performance:

1. **Non-ideal heat exchanger pinch analysis** — the 200 K hardcoded cold return temperature is an approximation; a rigorous model would iterate to satisfy energy balance across all HX streams simultaneously.
2. **Pressure drops** in heat exchangers, piping, and valves (assumed zero throughout).
3. **Moisture and CO₂ removal** (air purification unit) upstream of liquefaction.
4. **Thermocline degradation** in packed bed HGCS across repeated cycles.
5. **Part-load and off-design behaviour** — efficiency curves vs. load fraction are not implemented.
6. **Ambient temperature variation** — a fixed 25 °C is assumed; compressor performance is sensitive to ambient conditions.
7. **LNG/waste cold integration** — the model is standalone LAES only.
8. **Parasitic electrical loads** (instrumentation, controls, trace heating, lighting).
9. **Start-up energy and time** — assumed instantaneous and zero-energy.
10. **Geographic and site-specific factors** (altitude, grid connection costs, permitting).

---

## 9. Cross-Reference to Literature

| Metric | This Model | Literature (Borri et al. 2021, Tafone et al.) | Notes |
|---|---|---|---|
| Liquid yield (no cold recycle) | ~31% | 22–35% at 40–50 bar | ✓ In range |
| Liquid yield (with cold recycle) | ~38% | 35–45% | ✓ In range |
| Specific consumption (SC) | 0.381 kWh/kg | 0.35–0.45 kWh/kg (commercial) | ✓ Matches commercial scale |
| Specific power output (SP) | 0.099 kWh/kg | 0.20–0.35 kWh/kg (4-stage, optimised) | ⚠️ Low — 2 turbine stages vs. 4 in literature |
| RTE (standalone, no cold) | 26.1% | 45–55% (optimised) | ⚠️ Low due to 2-stage turbine and 200 °C superheat cap |
| RTE (standalone, with cold) | 28.4% | 50–62% (optimised) | ⚠️ Low for same reason |
| CAPEX ($/kW) | ~$2,400/kW (10 MW plant) | $900–6,000/kW | ✓ Reasonable for small-scale |
| LCOS | ~$769/MWh | $150–250/MWh (large, optimised) | ⚠️ High due to low RTE and small scale |

---

*Last updated: February 2026*
*Author: Inigo Antony*
