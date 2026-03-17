"""Spike Ensemble — main loop.

Ties together the sequencer, decoder, coherence engine, and MIDI output
into a closed-loop system where living neurons produce generative music.
"""

import time

import cl

from .channels import PITCH_NAMES
from .sequencer import Sequencer
from .decoder import Decoder
from .coherence import compute_coherence, CoherenceTracker
from .midi_output import MidiOutput


# ── Performance phases ──
PHASE_LISTENING    = 'listening'     # neurons receive context, no output
PHASE_FIRST_NOTES  = 'first_notes'   # decoding begins, expect noise
PHASE_LEARNING     = 'learning'      # feedback intensifies, convergence
PHASE_JAMMING      = 'jamming'       # reduced feedback, free exploration
PHASE_CHALLENGE    = 'challenge'     # key/tempo changes (optional)

PHASE_BOUNDARIES = {
    PHASE_LISTENING:   0,
    PHASE_FIRST_NOTES: 5,
    PHASE_LEARNING:    30,
    PHASE_JAMMING:     120,
    PHASE_CHALLENGE:   300,
}

SAMPLE_RATE = 25_000  # CL1 MEA sample rate in Hz


def get_phase(elapsed_seconds):
    """Return the current performance phase based on elapsed time."""
    if elapsed_seconds >= PHASE_BOUNDARIES[PHASE_CHALLENGE]:
        return PHASE_CHALLENGE
    elif elapsed_seconds >= PHASE_BOUNDARIES[PHASE_JAMMING]:
        return PHASE_JAMMING
    elif elapsed_seconds >= PHASE_BOUNDARIES[PHASE_LEARNING]:
        return PHASE_LEARNING
    elif elapsed_seconds >= PHASE_BOUNDARIES[PHASE_FIRST_NOTES]:
        return PHASE_FIRST_NOTES
    else:
        return PHASE_LISTENING


def run(bpm=120, duration_seconds=600, spike_threshold=3,
        chord_progression=None, default_octave=4, midi_port=None):
    """Run the Spike Ensemble performance.

    Args:
        bpm: beats per minute (default 120)
        duration_seconds: total performance duration
        spike_threshold: min spikes per pitch channel to trigger a note
        chord_progression: list of (name, [pitch_classes]) tuples
        default_octave: MIDI octave for note output
        midi_port: MIDI output port name (None = auto-detect)
    """
    sequencer = Sequencer(bpm=bpm, chord_progression=chord_progression)
    decoder = Decoder(spike_threshold=spike_threshold)
    coherence_tracker = CoherenceTracker(smoothing=0.1)
    midi = MidiOutput(port_name=midi_port, default_octave=default_octave)

    # One tick per 16th-note subdivision: 120 BPM = 8 subdivisions/sec
    subdivisions_per_second = (bpm * 4) / 60
    ticks_per_second = int(subdivisions_per_second)

    print(f"╔══════════════════════════════════════════╗")
    print(f"║         SPIKE ENSEMBLE                   ║")
    print(f"║     Living Neurons That Jam              ║")
    print(f"╠══════════════════════════════════════════╣")
    print(f"║  BPM: {bpm:<6} Duration: {duration_seconds}s             ║")
    print(f"║  Threshold: {spike_threshold:<4} Octave: {default_octave}               ║")
    print(f"║  Loop rate: {ticks_per_second} ticks/sec               ║")
    print(f"╚══════════════════════════════════════════╝")

    with cl.open() as neurons:
        recording = neurons.record(
            attributes={
                'app': 'spike_ensemble',
                'bpm': bpm,
                'spike_threshold': spike_threshold,
            }
        )

        # Data streams for visualization
        music_stream = neurons.create_data_stream(
            name='spike_ensemble',
            attributes={
                'bpm': bpm,
                'current_beat': 0,
                'current_chord': sequencer.current_chord_name,
                'coherence': 0.0,
                'phase': PHASE_LISTENING,
                'notes_played': [],
            }
        )

        coherence = 0.5
        last_phase = PHASE_LISTENING
        notes_total = 0
        phase_start = time.time()

        for tick in neurons.loop(
            ticks_per_second=ticks_per_second,
            stop_after_seconds=duration_seconds,
        ):
            timestamp = neurons.timestamp()
            elapsed = time.time() - phase_start
            phase = get_phase(elapsed)

            # Phase transition logging
            if phase != last_phase:
                print(f"\n>> Phase: {phase.upper().replace('_', ' ')} ({elapsed:.0f}s)")
                last_phase = phase

            # Collect all spikes from this tick's analysis window
            window_spikes = list(tick.analysis.spikes)

            # ── DECODE (after listening phase) ──
            decoded = None
            if phase != PHASE_LISTENING:
                frames_per_subdivision = int(SAMPLE_RATE * sequencer.subdivision_duration_ms / 1000)
                decoded = decoder.decode(
                    window_spikes,
                    window_start_ts=timestamp - frames_per_subdivision,
                    window_duration_ms=sequencer.subdivision_duration_ms,
                )

                # ── COHERENCE ──
                raw_coherence = compute_coherence(
                    decoded.notes,
                    sequencer.current_chord_tones,
                    sequencer.bar_position,
                    decoded.velocity,
                )
                coherence = coherence_tracker.update(raw_coherence)

                # ── MIDI OUTPUT ──
                if decoded.notes:
                    midi.send_event(decoded, octave=default_octave)
                    notes_total += len(decoded.notes)

                    note_names = [PITCH_NAMES[n] for n in decoded.notes]
                    if sequencer.bar_position % 4 == 0:  # Log on beat boundaries
                        print(
                            f"  beat {sequencer.bar_position:2d} | "
                            f"{sequencer.current_chord_name:5s} | "
                            f"notes: {','.join(note_names):12s} | "
                            f"vel: {decoded.velocity:3d} | "
                            f"coh: {coherence:.3f}"
                        )

            # ── DATA STREAM (all phases, so frontend timer stays in sync) ──
            music_stream.append(timestamp, {
                'beat': sequencer.bar_position,
                'chord': sequencer.current_chord_name,
                'notes': decoded.notes if decoded else [],
                'velocity': decoded.velocity if decoded else 0,
                'coherence': round(coherence, 3),
                'phase': phase,
                'notes_total': notes_total,
                'trend': round(coherence_tracker.trend(), 4),
            })

            # ── STIMULATE ──
            feedback_coherence = coherence
            if phase == PHASE_LISTENING:
                feedback_coherence = 0.5
            elif phase == PHASE_FIRST_NOTES:
                feedback_coherence = 0.4 + coherence * 0.3
            elif phase == PHASE_JAMMING:
                feedback_coherence = 0.5 + coherence * 0.2

            sequencer.deliver_all(neurons, coherence=feedback_coherence)

            # ── ADVANCE POSITION ──
            sequencer.advance()

            # Reset window
            window_spikes = []

        # ── Cleanup ──
        recording.stop()
        midi.close()

        print(f"\n{'='*44}")
        print(f"Performance complete.")
        print(f"  Total notes: {notes_total}")
        print(f"  Final coherence: {coherence:.3f}")
        print(f"  Trend: {coherence_tracker.trend():+.4f}")
        print(f"{'='*44}")


if __name__ == '__main__':
    run()
