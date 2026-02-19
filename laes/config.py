"""
LAES Configuration Module
=========================

All configurable parameters for the LAES model.

Author: Inigo Antony
License: MIT
"""

from dataclasses import dataclass


# Physical constants
SECONDS_PER_HOUR = 3600
HOURS_PER_DAY = 24
HOURS_PER_YEAR = 8760
T_LIQUID_AIR_K = 78.9       # Boiling point of air at 1 atm [K] — CoolProp verified
RHO_LIQUID_AIR = 875.0      # Density of liquid air at boiling point [kg/m³] — CoolProp verified


@dataclass
class PlantConfig:
    """
    Complete LAES plant configuration.

    All parameters needed to define a LAES system including:
    - Plant sizing (power, duration, tank)
    - Cycle parameters (pressures, temperatures, efficiencies)
    - Thermal storage parameters
    - Economic assumptions

    See ASSUMPTIONS.md for detailed justification of every default value.

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
    """Minimum tank level for cryogenic pump NPSH [%]"""

    boiloff_pct_per_day: float = 0.2
    """Tank boil-off rate [%/day] — consistent with commercial vacuum-jacketed tanks"""

    # ═══════════════════════════════════════════════════════════════════════
    # CYCLE PARAMETERS
    # ═══════════════════════════════════════════════════════════════════════

    P_charge_bar: float = 50.0
    """
    Liquefaction cycle high pressure [bar].
    50 bar is within the optimal range for the Claude/Kapitza cycle
    (Borri et al. 2021; Abdo et al. 2015). Higher pressures reduce
    specific consumption but increase compression work.
    """

    P_discharge_bar: float = 70.0
    """
    Power recovery cycle high pressure [bar].
    70 bar is a representative value used in several literature studies
    (Guizzi et al. 2015; Tafone et al. 2019). Higher than charge
    pressure to maximise turbine expansion ratio.
    """

    T_ambient_C: float = 25.0
    """Ambient temperature [°C]"""

    T_superheat_C: float = 250.0
    """
    Turbine inlet temperature [°C].
    250 °C represents stored compression heat used as a superheating source,
    consistent with the waste-heat-only (no external heat) scenario studied
    in Guizzi et al. (2015). Increasing to 300–350 °C raises RTE by 3–5%
    but requires an external heat source (see ASSUMPTIONS.md §3).
    """

    n_compressor_stages: int = 3
    """
    Number of compression stages with intercooling.
    3 stages at 50 bar total pressure ratio (≈ 3.7 per stage) is standard
    for industrial air compressors in this pressure range.
    """

    n_turbine_stages: int = 4
    """
    Number of turbine expansion stages with inter-stage reheat.
    4 stages matches the Highview Power pilot plant design and literature
    consensus (Tafone et al. 2019; Guizzi et al. 2015). 2 stages reduces
    SP from ~0.115 to ~0.099 kWh/kg — see ASSUMPTIONS.md §3.
    """

    bypass_fraction: float = 0.45
    """
    Fraction of compressed flow diverted to the bypass (cryogenic) turbine
    in the Claude cycle. Literature optimum for 40–60 bar charge pressure
    is 0.38–0.50 (Abdo et al. 2015; Borri et al. 2021). Default 0.45 is
    the midpoint of this range. Sensitivity: ±0.05 changes liquid yield
    by approximately ±1.5 percentage points.
    """

    # ═══════════════════════════════════════════════════════════════════════
    # COMPONENT EFFICIENCIES
    # ═══════════════════════════════════════════════════════════════════════

    eta_compressor: float = 0.85
    """
    Compressor isentropic efficiency.
    Appropriate for large-scale (> 5 MW) centrifugal or axial compressors.
    For smaller reciprocating or screw machines (< 2 MW), 0.75–0.82 is more
    realistic. See ASSUMPTIONS.md §4.
    """

    eta_cryo_turbine: float = 0.80
    """
    Cryogenic (bypass) turbine isentropic efficiency.
    Radial turboexpanders at cryogenic conditions: 0.78–0.85 (Borri et al. 2021).
    """

    eta_turbine: float = 0.85
    """
    Power recovery turbine isentropic efficiency.
    Consistent with high-efficiency radial inflow turbines at 70 bar inlet
    (Tafone et al. 2019; Guizzi et al. 2015).
    """

    eta_pump: float = 0.75
    """
    Cryogenic pump isentropic efficiency.
    Typical range 0.70–0.80 for reciprocating cryogenic pumps (Morgan et al. 2015).
    """

    hx_effectiveness: float = 0.90
    """
    Heat exchanger effectiveness (ε = actual / maximum possible heat transfer).
    0.90 is representative for well-designed plate-fin or spiral-wound cryogenic
    HEX (Popov et al. cited in Borri et al. 2021). Approach temperature ≈ 5–10 K.
    """

    # ═══════════════════════════════════════════════════════════════════════
    # THERMAL STORAGE
    # ═══════════════════════════════════════════════════════════════════════

    hot_storage_loss_pct_per_day: float = 1.0
    """
    Hot thermal storage (compression heat) loss rate [%/day].
    1.0 %/day is consistent with well-insulated thermal oil tanks at 200–300 °C
    (industrial sensible heat stores: 0.5–1.5 %/day). Sensitivity to hot storage
    losses on RTE is approximately 7× lower than cold storage losses (Peng et al. 2017).
    """

    hot_storage_efficiency: float = 0.90
    """Hot storage round-trip efficiency (charge/discharge combined)"""

    cold_storage_loss_pct_per_day: float = 5.0
    """
    Cold thermal storage (HGCS) heat gain rate [%/day].
    Higher loss rate reflects imperfect insulation of packed-bed cold stores
    at cryogenic temperatures. A 5% loss reduces cold benefit but remains
    within engineered tolerance for daily cycling.
    """

    cold_storage_efficiency: float = 0.85
    """
    Cold storage round-trip efficiency.
    0.85 represents packed-bed HGCS performance (Sciacovelli et al. 2017;
    Highview Power pilot data in Morgan et al. 2015). Accounts for thermocline
    degradation and imperfect heat exchange.
    """

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
    """
    Project lifetime [years].
    LAES uses industrial components (compressors, turbines, tanks) with 25–40 year
    lifetimes (Borri et al. 2021, Table 1). No electrochemical degradation.
    """

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
        """
        Intercooler outlet temperature [K] — fixed at 35 °C (308.15 K).
        Standard industrial intercooling target; matches Highview pilot plant
        and Tafone et al. (2019) configuration.
        """
        return 308.15  # 35 °C

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
  Turbine Stages:     {self.n_turbine_stages}
  Bypass Fraction:    {self.bypass_fraction:.2f}
  Compressor η:       {self.eta_compressor:.0%}
  Turbine η:          {self.eta_turbine:.0%}

Thermal Storage:
  Hot Storage Loss:   {self.hot_storage_loss_pct_per_day:.1f}%/day
  Cold Storage Loss:  {self.cold_storage_loss_pct_per_day:.1f}%/day
  Cold Store η:       {self.cold_storage_efficiency:.0%}

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
