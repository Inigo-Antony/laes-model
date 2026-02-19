# LAES — Liquid Air Energy Storage Model

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A first-principles thermodynamic and economic model for Liquid Air Energy Storage (LAES) systems, built on CoolProp for accurate real-gas property calculations.

---

## What is LAES?

Liquid Air Energy Storage stores electricity by:

1. **Charging** — liquefying air during off-peak hours using cheap electricity (~−196 °C)
2. **Storing** — holding liquid air in insulated tanks at near-atmospheric pressure
3. **Discharging** — expanding the liquid air through turbines during peak demand to regenerate electricity

Key advantages over other large-scale storage technologies:

- No geographical constraints (unlike pumped hydro)
- No electrochemical degradation (unlike batteries) — 25–40 year system life
- Uses proven industrial components (compressors, turbines, heat exchangers)
- Volumetric energy density ~200 kWh/m³ — roughly 6× denser than compressed air storage

---

## Model Features

| Module | What it does |
|--------|--------------|
| `thermodynamics.py` | Claude cycle liquefaction + multi-stage direct expansion power recovery |
| `storage.py` | Liquid air tank (boil-off) and thermal energy stores (HGCS/HGWS) |
| `simulation.py` | Time-domain operation over configurable charge/discharge schedules |
| `economics.py` | CAPEX, OPEX, NPV, payback, LCOS analysis |
| `cli.py` | Command-line interface |

---

## Quick Start

### Installation

```bash
git clone https://github.com/Inigo-Antony/laes-model.git
cd laes-model
pip install -r requirements.txt
pip install -e .
```

### Command Line

```bash
# Default 10 MW / 4-hour plant
python -m laes

# 50 MW / 6-hour plant
python -m laes --power 50 --hours 6 --tank 1000

# Different electricity price spread
python -m laes --offpeak 20 --onpeak 150

# 48-hour simulation with cold recycle
python -m laes --schedule two_day
```

### Python API

```python
from laes import PlantConfig, LAESSimulator, calculate_rte, calculate_economics

# Configure plant
config = PlantConfig(
    charge_power_MW=50,
    discharge_power_MW=50,
    storage_duration_hours=6,
    tank_capacity_tonnes=1000,
)

# Thermodynamic performance
rte = calculate_rte(config, verbose=True)
print(f"RTE (with cold recycle): {rte['rte_with_cold']:.1%}")
print(f"Specific consumption:    {rte['liquefaction_with_cold']['specific_consumption_kWh_per_kg']:.3f} kWh/kg")

# Transient simulation
sim = LAESSimulator(config)
results = sim.run([('charge', 8), ('idle', 4), ('discharge', 6)], verbose=True)
sim.plot_results('simulation.png')

# Economic analysis
econ = calculate_economics(config, rte=rte['rte_with_cold'], verbose=True)
print(f"CAPEX: ${econ['capex_total']/1e6:.1f} M")
print(f"LCOS:  ${econ['lcos_per_MWh']:.0f}/MWh")
```

---

## Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--power` | 10 | Plant power rating [MW] |
| `--hours` | 4 | Storage duration [hours] |
| `--tank` | 200 | Liquid air tank capacity [tonnes] |
| `--offpeak` | 30 | Off-peak electricity price [$/MWh] |
| `--onpeak` | 80 | On-peak electricity price [$/MWh] |
| `--schedule` | two_day | Operating schedule (`default`, `two_day`, `peak_shaving`) |
| `--output` | laes_simulation.png | Plot output filename |
| `--no-plot` | — | Skip plot generation |
| `--quiet` | — | Suppress detailed output |

---

## Cycle Overview

### Liquefaction (Charge) — Claude Cycle

```
Air (25°C, 1 bar)
  → [3-stage Compressor + Intercooling to 35°C]
  → [HX1: pre-cooled by cold return stream*]
  → [Cold-Store HX: further pre-cooled by HGCS cold (if available)]
  → Flow split (bypass_fraction = 0.45):
       bypass  → [Cryogenic Turbine] → cold exhaust → HX1 return
       main    → [HX2] → [J-T valve] → [Phase Separator]
                                              ↓           ↓
                                        Liquid Air    Vapour → HX1 return
                                        to Tank
```

*Cold return temperature is derived from a mass-enthalpy balance of the bypass exhaust and phase separator vapour — not a hardcoded assumption.

### Power Recovery (Discharge) — Direct Expansion

```
Liquid Air (tank)
  → [Cryogenic Pump: 1 → 70 bar]
  → [Cold Recovery to HGCS* (pump outlet to 35°C)]
  → [Evaporator + Superheater: to 250°C using stored compression heat]
  → [4-stage Turbine with inter-stage reheat]
  → Electricity
```

*Cold recovery upper bound is T_intercool (35°C) — the physically correct cutoff for cold that is useful to the liquefaction cycle.

---

## Model Performance (Default 10 MW / 4-hour Plant)

| Metric | Model Value | Literature Range | Notes |
|--------|-------------|-----------------|-------|
| Liquid yield (no cold) | ~31% | 22–35% (Claude, 50 bar) | ✅ In range |
| Liquid yield (with cold) | ~38% | 35–45% | ✅ In range |
| Specific consumption SC (no cold) | ~0.38 kWh/kg | 0.35–0.45 kWh/kg | ✅ Commercial scale range |
| Specific consumption SC (with cold) | ~0.34 kWh/kg | 0.30–0.40 kWh/kg | ✅ In range |
| Specific power output SP | ~0.115 kWh/kg | 0.10–0.35 kWh/kg | ✅ 4-stage turbine |
| RTE (no cold) | ~30% | — | Steady-state, no external heat |
| RTE (with cold recycle) | ~33% | 45–62% (large, optimised) | See gap analysis below |
| CAPEX (10 MW) | ~$24–28 M | $900–6,000/kW | ✅ Small-scale range |
| LCOS | ~$400–500/MWh | $150–250/MWh (large) | Consequence of low RTE at small scale |

### Why is the RTE lower than literature?

Literature figures of 45–62% typically include:
- **External heat sources** (waste heat from co-located LNG terminals, power stations, or industrial processes) raising turbine inlet temperature to 300–400 °C vs. 250 °C here
- **Large-scale effects** (50–200 MW plants with optimised component selection)
- **Hybrid configurations** (ORC integration, LNG cold recovery)

This model represents a **stand-alone, self-contained 10 MW plant with no external heat/cold**. The Highview Power 5 MW pilot achieved **8% RTE** in early trials (Morgan et al. 2015). Their commercial 50 MW target is 50–60% RTE. At 10 MW stand-alone with stored compression heat only, 30–35% is physically plausible and consistent with the Sciacovelli et al. (2017) results for small-scale non-hybrid LAES.

Increasing `T_superheat_C` to 300–350 °C (available with external waste heat) raises RTE to approximately 40–45%.

---

## Assumptions

All modelling assumptions — every default value, hardcoded parameter, and simplification — are documented with physical justification and literature references in **[ASSUMPTIONS.md](ASSUMPTIONS.md)**.

Key decisions worth noting:
- Cold return temperature to HX1 is **physically derived** from a mass-enthalpy balance (bypass turbine exhaust + phase separator vapour), not assumed
- Cold recovery upper bound is **T_intercool (35 °C)**, the physically correct cutoff
- 4 turbine stages with inter-stage reheat (consistent with Highview Power pilot design)
- No external heat or cold sources assumed — standalone worst case

---

## Project Structure

```
laes-model/
├── README.md               # This file
├── ASSUMPTIONS.md          # Full assumptions and justifications
├── requirements.txt
├── setup.py
│
├── laes/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── config.py           # PlantConfig dataclass + constants
│   ├── thermodynamics.py   # Liquefaction + discharge + RTE
│   ├── storage.py          # Tank and thermal storage models
│   ├── simulation.py       # Transient simulator + plots
│   └── economics.py        # CAPEX, OPEX, NPV, LCOS
│
├── examples/
│   └── example_usage.py
│
└── tests/
    └── test_laes.py
```

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

---

## Known Limitations

1. **Steady-state only** — dynamic operation (thermocline effects, start-up/shutdown) can reduce effective RTE by 20–25% (Sciacovelli et al. 2017; Vecchi et al. 2020). The HGCS efficiency factor (0.85) partially accounts for this.
2. **No part-load model** — all results are at 100% rated power.
3. **Non-iterative cold box** — HX1 cold-return temperature uses a first-pass estimate; a rigorous pinch analysis would iterate to convergence. Planned for a future release.
4. **No external heat/cold integration** — LNG cold recovery or industrial waste heat can double the RTE; modelling these is a known future extension.
5. **CAPEX uncertainty ±30–50%** — parametric pre-FEED estimates only.

See [ASSUMPTIONS.md §7](ASSUMPTIONS.md#7-limitations-and-known-simplifications) for full details.

---

## References

1. Borri et al. (2021). A review on liquid air energy storage. *Renewable and Sustainable Energy Reviews* 137, 110572.
2. Morgan et al. (2015). Liquid air energy storage — first results from a pilot scale plant. *Applied Energy* 137, 845–853.
3. Tafone et al. (2019). New parametric performance maps for LAES. *Applied Energy* 250, 1641–1656.
4. Guizzi et al. (2015). Thermodynamic analysis of a LAES system. *Energy* 93, 1639–1647.
5. Sciacovelli et al. (2017). LAES operation and performance, first pilot plant. *Applied Energy* 194, 522–529.

---

## Author

**Inigo Antony**  
MSc Sustainable Energy Systems — University of Birmingham / IIT Madras  
GitHub: [@Inigo-Antony](https://github.com/Inigo-Antony)  
Email: inigoantony16@gmail.com

## Acknowledgements

- [CoolProp](http://www.coolprop.org/) for thermodynamic property calculations
- [Highview Power](https://highviewpower.com/) for pioneering commercial LAES

---

*Licensed under the MIT License.*
