"""
LAES Storage Models
"""

import numpy as np


class ThermalStorage:
    def __init__(self, capacity_J: float, loss_rate_per_s: float, efficiency: float = 0.90):
        self.capacity_J = capacity_J
        self.loss_rate = loss_rate_per_s
        self.efficiency = efficiency
        self.charge_eff = np.sqrt(efficiency)
        self.discharge_eff = np.sqrt(efficiency)
        self.energy_J = 0.0
        self.total_charged_J = 0.0
        self.total_discharged_J = 0.0
        self.total_lost_J = 0.0
        self.overflow_J = 0.0

    @property
    def soc(self) -> float:
        return self.energy_J / self.capacity_J if self.capacity_J > 0 else 0

    def charge(self, energy_J: float) -> float:
        energy_after_loss = energy_J * self.charge_eff
        available = self.capacity_J - self.energy_J
        actually_stored = min(energy_after_loss, available)
        overflow = energy_after_loss - actually_stored
        self.energy_J += actually_stored
        self.total_charged_J += energy_J
        self.overflow_J += overflow
        return actually_stored

    def discharge(self, energy_requested_J: float) -> float:
        stored_needed = energy_requested_J / self.discharge_eff
        actually_used = min(stored_needed, self.energy_J)
        actually_delivered = actually_used * self.discharge_eff
        self.energy_J -= actually_used
        self.total_discharged_J += actually_delivered
        return actually_delivered

    def apply_losses(self, dt_s: float) -> float:
        E_before = self.energy_J
        self.energy_J *= np.exp(-self.loss_rate * dt_s)
        lost = E_before - self.energy_J
        self.total_lost_J += lost
        return lost


class LiquidAirTank:
    def __init__(self, capacity_kg: float, min_level_frac: float, boiloff_rate_per_s: float):
        self.capacity_kg = capacity_kg
        self.min_level_frac = min_level_frac
        self.boiloff_rate = boiloff_rate_per_s
        self.mass_kg = 0.0
        self.total_charged_kg = 0.0
        self.total_discharged_kg = 0.0
        self.total_boiloff_kg = 0.0

    @property
    def level(self) -> float:
        return self.mass_kg / self.capacity_kg

    @property
    def available_kg(self) -> float:
        min_mass = self.min_level_frac * self.capacity_kg
        return max(0, self.mass_kg - min_mass)

    def charge(self, mass_kg: float) -> float:
        available = self.capacity_kg - self.mass_kg
        actually_stored = min(mass_kg, available)
        self.mass_kg += actually_stored
        self.total_charged_kg += actually_stored
        return actually_stored

    def discharge(self, mass_kg: float) -> float:
        actually_discharged = min(mass_kg, self.available_kg)
        self.mass_kg -= actually_discharged
        self.total_discharged_kg += actually_discharged
        return actually_discharged

    def apply_boiloff(self, dt_s: float) -> float:
        m_before = self.mass_kg
        self.mass_kg *= np.exp(-self.boiloff_rate * dt_s)
        lost = m_before - self.mass_kg
        self.total_boiloff_kg += lost
        return lost
