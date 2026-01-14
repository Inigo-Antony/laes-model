"""
LAES Command Line Interface
===========================

Main entry point for running LAES analysis from command line.

Usage:
    python -m laes [options]
    
    or after installation:
    
    laes [options]

Author: [Your Name]
License: MIT
"""

import argparse
import sys

from .config import PlantConfig, SCHEDULES
from .thermodynamics import calculate_rte
from .simulation import LAESSimulator
from .economics import calculate_economics


def parse_args(args=None):
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        prog='laes',
        description='LAES (Liquid Air Energy Storage) Model',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m laes                              # Default 10 MW / 4-hour plant
    python -m laes --power 50 --hours 6         # 50 MW / 6-hour plant
    python -m laes --offpeak 20 --onpeak 120    # Different electricity prices
    python -m laes --schedule two_day           # 48-hour simulation
    python -m laes --output results.png         # Custom output filename
        """
    )
    
    # Plant sizing
    parser.add_argument(
        '--power', type=float, default=10.0,
        help='Plant power rating [MW] (default: 10)'
    )
    parser.add_argument(
        '--hours', type=float, default=4.0,
        help='Storage duration [hours] (default: 4)'
    )
    parser.add_argument(
        '--tank', type=float, default=200.0,
        help='Tank capacity [tonnes] (default: 200)'
    )
    
    # Electricity prices
    parser.add_argument(
        '--offpeak', type=float, default=30.0,
        help='Off-peak electricity price [$/MWh] (default: 30)'
    )
    parser.add_argument(
        '--onpeak', type=float, default=80.0,
        help='On-peak electricity price [$/MWh] (default: 80)'
    )
    
    # Simulation
    parser.add_argument(
        '--schedule', type=str, default='two_day',
        choices=list(SCHEDULES.keys()),
        help='Operating schedule (default: two_day)'
    )
    
    # Output
    parser.add_argument(
        '--output', type=str, default='laes_simulation.png',
        help='Output plot filename (default: laes_simulation.png)'
    )
    parser.add_argument(
        '--no-plot', action='store_true',
        help='Skip generating plots'
    )
    parser.add_argument(
        '--quiet', action='store_true',
        help='Suppress detailed output'
    )
    
    return parser.parse_args(args)


def main(args=None):
    """Main entry point"""
    args = parse_args(args)
    verbose = not args.quiet
    
    # Create configuration
    cfg = PlantConfig(
        charge_power_MW=args.power,
        discharge_power_MW=args.power,
        storage_duration_hours=args.hours,
        tank_capacity_tonnes=args.tank,
        price_offpeak_MWh=args.offpeak,
        price_onpeak_MWh=args.onpeak,
    )
    
    if verbose:
        print("=" * 70)
        print(" LAES MODEL - LIQUID AIR ENERGY STORAGE")
        print("=" * 70)
        print(cfg.summary())
    
    # ═══ THERMODYNAMIC ANALYSIS ═══
    if verbose:
        print("\n" + "█" * 70)
        print("  THERMODYNAMIC ANALYSIS")
        print("█" * 70)
    
    rte_result = calculate_rte(cfg, verbose=verbose)
    
    # ═══ TRANSIENT SIMULATION ═══
    if verbose:
        print("\n" + "█" * 70)
        print("  TRANSIENT SIMULATION")
        print("█" * 70)
    
    schedule = SCHEDULES[args.schedule]
    sim = LAESSimulator(cfg)
    sim_results = sim.run(schedule, verbose=verbose)
    
    if not args.no_plot:
        sim.plot_results(save_path=args.output, show=False)
    
    # ═══ ECONOMIC ANALYSIS ═══
    if verbose:
        print("\n" + "█" * 70)
        print("  ECONOMIC ANALYSIS")
        print("█" * 70)
    
    econ = calculate_economics(cfg, rte=rte_result['rte_with_cold'], verbose=verbose)
    
    # ═══ SUMMARY ═══
    print("\n" + "=" * 70)
    print(" SUMMARY")
    print("=" * 70)
    
    print(f"\n Plant Configuration:")
    print(f"   Power:    {args.power:.0f} MW")
    print(f"   Duration: {args.hours:.0f} hours")
    print(f"   Capacity: {args.power * args.hours:.0f} MWh")
    
    print(f"\n Performance:")
    print(f"   RTE (steady-state): {rte_result['rte_with_cold']:.1%}")
    print(f"   RTE (simulated):    {sim_results['round_trip_efficiency']:.1%}")
    
    print(f"\n Economics:")
    print(f"   CAPEX:   ${econ['capex_total']/1e6:.1f} million")
    print(f"   NPV:     ${econ['npv']/1e6:.1f} million")
    print(f"   LCOS:    ${econ['lcos_per_MWh']:.0f}/MWh")
    
    if not args.no_plot:
        print(f"\n Plot saved to: {args.output}")
    
    print("\n" + "=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
