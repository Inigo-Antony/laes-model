#!/usr/bin/env python3
"""
LAES Example Usage
==================

This script demonstrates how to use the LAES package programmatically.

Run this script from the repository root:
    python examples/example_usage.py
"""

import sys
import os

# Add parent directory to path (if running from examples/)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from laes import (
    PlantConfig,
    LAESSimulator,
    calculate_rte,
    calculate_economics,
    SCHEDULES,
)


def main():
    """Demonstrate LAES package usage"""
    
    print("=" * 70)
    print(" LAES Package - Example Usage")
    print("=" * 70)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 1: Basic Usage
    # ═══════════════════════════════════════════════════════════════════════
    
    print("\n" + "─" * 70)
    print(" Example 1: Basic Usage with Default Configuration")
    print("─" * 70)
    
    # Create default configuration
    config = PlantConfig()
    print(config.summary())
    
    # Calculate round-trip efficiency
    rte_result = calculate_rte(config, verbose=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 2: Custom Configuration
    # ═══════════════════════════════════════════════════════════════════════
    
    print("\n" + "─" * 70)
    print(" Example 2: Custom 50 MW / 6-Hour Plant")
    print("─" * 70)
    
    large_plant = PlantConfig(
        charge_power_MW=50,
        discharge_power_MW=50,
        storage_duration_hours=6,
        tank_capacity_tonnes=1000,
        price_offpeak_MWh=20,
        price_onpeak_MWh=120,
    )
    
    print(f"\n Configuration:")
    print(f"   Power: {large_plant.charge_power_MW} MW")
    print(f"   Duration: {large_plant.storage_duration_hours} hours")
    print(f"   Tank: {large_plant.tank_capacity_tonnes} tonnes")
    print(f"   Price spread: ${large_plant.price_onpeak_MWh - large_plant.price_offpeak_MWh}/MWh")
    
    rte_large = calculate_rte(large_plant, verbose=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 3: Transient Simulation
    # ═══════════════════════════════════════════════════════════════════════
    
    print("\n" + "─" * 70)
    print(" Example 3: Transient Simulation")
    print("─" * 70)
    
    # Use default config
    sim = LAESSimulator(config)
    
    # Run 48-hour simulation
    schedule = SCHEDULES['two_day']
    print(f"\n Schedule (48 hours):")
    for mode, duration in schedule:
        print(f"   {mode.upper()}: {duration} hours")
    
    results = sim.run(schedule, verbose=True)
    
    # Plot results
    sim.plot_results(save_path='laes_example_simulation.png', show=False)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 4: Economic Analysis
    # ═══════════════════════════════════════════════════════════════════════
    
    print("\n" + "─" * 70)
    print(" Example 4: Economic Analysis")
    print("─" * 70)
    
    econ = calculate_economics(config, rte=rte_result['rte_with_cold'], verbose=True)
    
    # ═══════════════════════════════════════════════════════════════════════
    # EXAMPLE 5: Sensitivity Study
    # ═══════════════════════════════════════════════════════════════════════
    
    print("\n" + "─" * 70)
    print(" Example 5: Sensitivity to Electricity Price Spread")
    print("─" * 70)
    
    print(f"\n {'Spread ($/MWh)':<20} {'NPV ($M)':<15} {'LCOS ($/MWh)':<15}")
    print(f" {'─'*50}")
    
    for spread in [30, 50, 80, 100, 150]:
        test_config = PlantConfig(
            price_offpeak_MWh=30,
            price_onpeak_MWh=30 + spread,
        )
        rte = calculate_rte(test_config, verbose=False)['rte_with_cold']
        econ = calculate_economics(test_config, rte=rte, verbose=False)
        
        print(f" ${spread:<19} ${econ['npv']/1e6:<14.1f} ${econ['lcos_per_MWh']:<14.0f}")
    
    # ═══════════════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════════════
    
    print("\n" + "=" * 70)
    print(" Example Complete!")
    print("=" * 70)
    print("\n Output files generated:")
    print("   - laes_example_simulation.png")
    print("\n For more options, run: python -m laes --help")


if __name__ == "__main__":
    main()
