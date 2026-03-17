#!/usr/bin/env python3
"""Quick-start runner for Spike Ensemble.

Usage:
    python run.py                    # Default: 120 BPM, 10 min
    python run.py --bpm 90           # Slower tempo
    python run.py --duration 120     # 2 minute session
    python run.py --threshold 2      # More sensitive note detection
"""

import argparse
import sys
import os

# Ensure src/ is importable
sys.path.insert(0, os.path.dirname(__file__))


def main():
    parser = argparse.ArgumentParser(description='Spike Ensemble — Living Neurons That Jam')
    parser.add_argument('--bpm', type=int, default=120, help='Beats per minute (default: 120)')
    parser.add_argument('--duration', type=int, default=600, help='Duration in seconds (default: 600)')
    parser.add_argument('--threshold', type=int, default=3, help='Spike threshold for note detection (default: 3)')
    parser.add_argument('--octave', type=int, default=4, help='Default MIDI octave (default: 4)')
    parser.add_argument('--midi-port', type=str, default=None, help='MIDI output port name')
    args = parser.parse_args()

    from src.main import run

    run(
        bpm=args.bpm,
        duration_seconds=args.duration,
        spike_threshold=args.threshold,
        default_octave=args.octave,
        midi_port=args.midi_port,
    )


if __name__ == '__main__':
    main()
