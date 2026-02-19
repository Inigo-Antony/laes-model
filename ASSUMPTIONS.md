# LAES Model — Assumptions and Modelling Decisions

**Version:** 1.1.0  
**Author:** Inigo Antony  
**Last updated:** February 2026

This document records every modelling assumption, hardcoded value, and simplification in the LAES model, with physical justification and literature references. It is intended for readers who want to understand the basis of the model before using it in a technical or commercial context.

---

## 1. Working Fluid

| Assumption | Value | Justification |
|---|---|---|
| Working fluid | CoolProp `'Air'` pseudo-pure fluid | Air at cryogenic temperatures is ~78% N₂, ~21% O₂, ~1% Ar. CoolProp's `'Air'` mixture reproduces thermodynamic properties to within ~2% of a rigorous mixture calculation. Error on RTE from this simplification is < 2% (Borri et al. 2021). |
| Ambient pressure | 101 325 Pa | ISO standard atmosphere |
| Ambient temperature | 25 °C (configurable) | Temperate climate baseline. Cold climates reduce compression work; the model is conservative by using 25 °C. |

---

## 2. Liquefaction Cycle (Claude Cycle)

### 2.1 Cycle configuration

The model implements a **Claude cycle** (not Linde–Hampson or Kapitza). The Claude cycle was identified as the best cost-performance option for LAES by Abdo et al. (2015) due to its fewer components compared to Collins cycles while achieving comparable liquid yield. The Highview Power pilot plant used a single-turbine Claude design (Morgan et al. 2015).

### 2.2 Compression: number of stages and intercooling temperature

| Parameter | Default | Justification |
|---|---|---|
| Stages | 3 | Standard for 50 bar pressure ratio (≈ 3.7 per stage) in industrial air compressors. Borri et al. 2021; Guizzi et al. 2015. |
| Intercooler outlet temperature | 35 °C (308.15 K) | Representative industrial intercooling target. Fixed (not configurable) as it has low sensitivity compared to charge pressure. |
| Compressor isentropic efficiency | 0.85 | Appropriate for large (> 5 MW) centrifugal or axial machines. For smaller screw/reciprocating compressors (< 2 MW), 0.75–0.82 is more realistic. Sensitivity: ±0.02 in η changes RTE by ≈ ±1.5%. |

### 2.3 HX1 cold return temperature — physically derived

**Prior version:** hardcoded `T_cold_return = 200 K` (undocumented).

**Current version:** derived from a mass-enthalpy balance of the two streams returning to HX1:

```
Stream A (mass fraction = bypass_frac):
    Bypass turbine exhaust — expanded from T_intercool to P_ambient
    (T_intercool is an upper-bound estimate of the bypass turbine inlet;
     the true inlet is lower because HX1 pre-cools it first)

Stream B (mass fraction ≈ main_frac × (1 − Y_approx)):
    Phase separator saturated vapour — CoolProp: T_sat(P_ambient, Q=1) ≈ 78.9 K

Mixed return temperature:
    h_return = (bypass_frac × h_A + vapor_frac × h_B) / total_return_frac
    T_cold_return = CoolProp(H=h_return, P=P_ambient)
```

Where `Y_approx = 0.30` is a first-pass liquid yield estimate used **only** for the mass-split calculation, not for the main liquid yield result.

**Limitation:** The bypass turbine inlet in reality is colder than T_intercool (because HX1 pre-cools it before the split). Using T_intercool produces a slightly too-warm T_bypass_out, giving a conservative (slightly under-estimated) T_cold_return. The error is small (< 5 K on T_cold_return). A rigorous value requires iteration (converging T_cold_return from the HX1 energy balance); this is planned for a future release.

**Typical result for default config:** T_cold_return ≈ 110–125 K, versus the prior hardcoded 200 K. The physically derived value gives a more realistic HX1 effectiveness and liquid yield.

### 2.4 Bypass fraction

| Parameter | Default | Justification |
|---|---|---|
| `bypass_fraction` | 0.45 | Literature optimum for 40–60 bar charge pressure in Claude/Kapitza cycle: 0.38–0.50 (Abdo et al. 2015; Borri et al. 2021 §3.1.1). 0.45 is the midpoint. Sensitivity: ±0.05 changes liquid yield by ≈ ±1.5 percentage points. |

### 2.5 Charge pressure

| Parameter | Default | Justification |
|---|---|---|
| `P_charge_bar` | 50 bar | Within the range yielding lowest specific consumption for Claude/Kapitza cycles (Abdo et al. 2015; Borri et al. 2021). Higher pressures (100–180 bar) are used in Linde–Hampson cycles. The Highview pilot used 13 bar (low, driving high specific consumption). |

---

## 3. Power Recovery (Discharge) Cycle

### 3.1 Turbine stages and inter-stage reheat

| Parameter | Default | Justification |
|---|---|---|
| `n_turbine_stages` | **4** | Literature consensus for optimised LAES: 4 stages with reheat (Highview Power pilot, 4-stage radial turbines; Tafone et al. 2019; Guizzi et al. 2015). 2 stages gives SP ≈ 0.099 kWh/kg; 4 stages gives SP ≈ 0.115 kWh/kg — a 16% improvement. |
| Reheat temperature | `T_superheat` at each inter-stage | Assumes sufficient stored heat is available at each stage inlet. This is optimistic for the later stages if the HGWS has limited capacity, but consistent with the thermodynamic reference cases in literature. |

### 3.2 Turbine inlet temperature (superheating)

| Parameter | Default | Justification |
|---|---|---|
| `T_superheat_C` | **250 °C** | Represents the maximum temperature achievable from stored compression heat (HGWS) without an external heat source. Guizzi et al. (2015) uses 268 °C from compression waste heat recycled via thermal oil. Literature cases using external waste heat (LNG, biomass) reach 300–400 °C with significantly higher RTE. |

**Sensitivity:** Increasing from 200 °C to 280 °C raises RTE by approximately 3–5 percentage points.

### 3.3 Cold recovery upper bound — T_intercool

**Prior version:** hardcoded `T_cold_end = −50 °C` (223.15 K).

**Current version:** `T_cold_end = T_intercool_K` (308.15 K, i.e., 35 °C).

**Physical justification:** The HGCS stores enthalpy extracted from the warming liquid air, from the pump outlet (~−194 °C at 70 bar) up to the highest temperature where cold is still useful for the liquefaction cycle. The liquefaction compressor returns air to T_intercool (35 °C) before entering the cold box. Cold above 35 °C therefore cannot pre-cool the high-pressure stream any further. T_intercool is thus the physically correct upper bound on recoverable cold.

The previous −50 °C cutoff understated cold recovery by approximately 20–30%. The packed-bed HGCS round-trip efficiency (`cold_storage_efficiency = 0.85`) accounts for real losses (thermocline degradation, heat gain through insulation). This efficiency is applied separately in `calculate_rte()`.

### 3.4 Discharge pressure

| Parameter | Default | Justification |
|---|---|---|
| `P_discharge_bar` | 70 bar | Higher than charge pressure (50 bar) to maximise turbine expansion ratio. Used in Guizzi et al. (2015) and Tafone et al. (2019). Discharge pump raises liquid from ~1 bar to 70 bar — incompressible work is small (≈ 10–15 kJ/kg). |

---

## 4. Component Efficiencies

| Component | Default η | Literature range | Notes |
|---|---|---|---|
| Compressor (isentropic) | 0.85 | 0.80–0.88 | Large centrifugal; reduce to 0.78 for small screw/recip |
| Cryogenic turbine (bypass) | 0.80 | 0.78–0.85 | Radial turboexpanders at cryogenic conditions |
| Power turbine (discharge) | 0.85 | 0.82–0.88 | Multi-stage radial inflow; consistent with Tafone et al. |
| Cryogenic pump | 0.75 | 0.70–0.82 | Reciprocating cryogenic pumps (Morgan et al. 2015) |
| Heat exchanger effectiveness | 0.90 | 0.85–0.95 | Plate-fin or spiral-wound cryogenic HEX |

All efficiencies are configurable via `PlantConfig`.

---

## 5. Thermal Storage

### 5.1 Cold storage (HGCS — High-Grade Cold Storage)

| Parameter | Value | Justification |
|---|---|---|
| `cold_storage_efficiency` | 0.85 | Packed-bed HGCS performance from Highview Power pilot (Morgan et al. 2015; Sciacovelli et al. 2017). Accounts for thermocline degradation (reduces effective cold by up to 25% compared to ideal). |
| `cold_storage_loss_pct_per_day` | 5 %/day | Conservative loss rate for packed-bed stores at cryogenic temperatures with ambient heat leak through insulation. Daily cycling mitigates accumulation. |

**Important note from Sciacovelli et al. (2017):** The thermocline effect in packed-bed HGCS can reduce LAES performance by up to 25% compared to nominal (steady-state) values. This model operates at steady-state and applies a round-trip efficiency factor (0.85) to account for this rather than modelling the thermocline directly.

### 5.2 Hot storage (HGWS — High-Grade Warm Storage)

| Parameter | Value | Justification |
|---|---|---|
| `hot_storage_efficiency` | 0.90 | Thermal oil tanks (e.g., Essotherm 650) at 200–300 °C. Used in Guizzi et al. (2015). |
| `hot_storage_loss_pct_per_day` | 1 %/day | Well-insulated thermal oil store; 0.5–1.5 %/day industrial range. **Note:** Hot storage losses affect RTE approximately 7× less than cold storage losses (Peng et al. 2017). |

### 5.3 Liquid air tank boil-off

| Parameter | Value | Justification |
|---|---|---|
| `boiloff_pct_per_day` | 0.2 %/day | Consistent with commercial vacuum-jacketed cryogenic storage tanks. Borri et al. (2021) Table 1 notes 0.1–0.2% per day for LAES. |

---

## 6. Economic Model

All cost figures are **parametric pre-FEED estimates with ±30–50% uncertainty**. They are suitable for comparative analysis and sensitivity studies but should not be used for investment decisions without vendor quotations.

| Parameter | Value | Basis |
|---|---|---|
| Compressor capital | $500/kW input | Engineering estimate |
| Turbine capital | $400/kW output | Engineering estimate |
| Cryogenic tank | $800/m³ | Industry reference for vacuum-jacketed cryogenic vessels |
| Hot thermal storage | $30/kWh thermal | Industrial thermal oil TES |
| Cold thermal storage | $45/kWh thermal | Packed-bed HGCS |
| Heat exchangers | $75/kW thermal | Parametric (sized by thermal power) |
| Balance of Plant | 20% of equipment | Standard engineering factor |
| Installation | 25% of equipment | Standard engineering factor |
| O&M | 1.5% CAPEX/year | No electrochemical degradation; largely mechanical maintenance |
| Insurance | 0.5% CAPEX/year | Standard infrastructure insurance |
| Capacity payment | $50/kW-year | Representative UK/US capacity market value. Actual values vary $0–$200/kW-year; this assumption has a material impact on NPV. |
| Discount rate | 8% real | Infrastructure project baseline |
| Project lifetime | 25 years | Conservative; industrial components rated 30–40 years |
| Performance degradation | 0.5%/year | Conservative; LAES has no electrochemical degradation. This factor is applied to annual cash flows only. |

---

## 7. Limitations and Known Simplifications

The following limitations should be declared when presenting model results to technical audiences:

| Limitation | Effect on results | Mitigation in this model |
|---|---|---|
| **Steady-state only** | Sciacovelli et al. (2017) and Vecchi et al. (2020) show dynamic operation reduces effective RTE by up to 25–30% compared to steady-state. | HGCS efficiency (0.85) partially accounts for thermocline losses. |
| **No part-load curves** | Compressor efficiency drops below ~60% load; turbine maps are non-linear. | All results are rated-power (100% load) only. |
| **Non-iterative cold box** | T_cold_return is derived from a first-pass estimate (bypass inlet = T_intercool). A rigorous pinch analysis would converge this via iteration. | Physically derived value vs. prior magic number. Future work: bisection iteration. |
| **Uniform air composition** | Real air separation effects are ignored. CoolProp `'Air'` is a pseudo-pure fluid. | Error on RTE < 2%. |
| **No plant self-consumption** | Auxiliary power (control systems, pumps, instrumentation) is not modelled. | Typically 1–2% of rated power; subtract from reported RTE if needed. |
| **No cycle-to-cycle mass balance enforcement** | The simulation module does not verify that liquid produced equals liquid consumed across a full cycle. | Use simulation results directionally; do not use for mass inventory optimisation. |
| **CAPEX uncertainty ±30–50%** | Pre-FEED estimates only. | Noted explicitly in output. Sensitivity analysis recommended. |

---

## 8. Literature References

1. **Borri et al. (2021)** — "A review on liquid air energy storage: History, state of the art and recent developments." *Renewable and Sustainable Energy Reviews* 137, 110572.

2. **Morgan et al. (2015)** — "Liquid air energy storage — Analysis and first results from a pilot scale demonstration plant." *Applied Energy* 137, 845–853.

3. **Tafone et al. (2019)** — "New parametric performance maps for a novel sizing and selection methodology of a Liquid Air Energy Storage system." *Applied Energy* 250, 1641–1656.

4. **Guizzi et al. (2015)** — "Thermodynamic analysis of a liquid air energy storage system." *Energy* 93, 1639–1647.

5. **Sciacovelli et al. (2017)** — "Liquid air energy storage — Operation and performance of the first pilot plant in the world." *Applied Energy* 194, 522–529.

6. **Abdo et al. (2015)** — "Performance evaluation of various air liquefaction cycles used in LAES systems." *Applied Thermal Engineering* 87, 603–612.

7. **Peng et al. (2017)** — "Investigation on the effects of cold and heat recovery on the performance of LAES." *Energy* 127, 495–502.

8. **Vecchi et al. (2020)** — "Liquid air energy storage (LAES): Packaging performance analysis and benchmarking with other storage technologies." *Sustainable Energy Technologies and Assessments* 37, 100630.

---

*Questions, corrections, and contributions welcome via GitHub Issues.*
