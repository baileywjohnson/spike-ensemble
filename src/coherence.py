"""Coherence scoring — evaluates how musically coherent the neural output is.

The coherence score (0.0–1.0) drives the free energy feedback loop:
high coherence → predictable stimulation (reward), low → noisy (punishment).
"""

from .sequencer import BEAT_WEIGHTS

# C major scale pitch classes
C_MAJOR_SCALE = {0, 2, 4, 5, 7, 9, 11}

# Common scales for different keys (pitch class sets)
MAJOR_SCALE_INTERVALS = [0, 2, 4, 5, 7, 9, 11]


def get_scale_tones(root=0):
    """Return pitch class set for a major scale starting on root."""
    return {(root + interval) % 12 for interval in MAJOR_SCALE_INTERVALS}


def compute_coherence(decoded_notes, chord_tones, beat_position, velocity,
                      scale_tones=None, harmony_weight=0.4,
                      rhythm_weight=0.4, dynamics_weight=0.2):
    """Score how musically coherent the neural output is.

    Args:
        decoded_notes: list of pitch classes (0–11) from decoder
        chord_tones: list of pitch classes in current chord
        beat_position: 0–15 (16th-note position in bar)
        velocity: MIDI velocity 0–127
        scale_tones: set of pitch classes in current scale (defaults to C major)
        harmony_weight: weight for harmonic fit score
        rhythm_weight: weight for rhythmic fit score
        dynamics_weight: weight for dynamics score

    Returns:
        float 0.0 (chaos) to 1.0 (perfectly musical)
    """
    if scale_tones is None:
        scale_tones = C_MAJOR_SCALE

    chord_set = set(chord_tones)

    # 1. HARMONIC FIT
    if decoded_notes:
        in_chord = sum(1 for n in decoded_notes if n in chord_set)
        in_scale = sum(1 for n in decoded_notes if n in scale_tones)
        harmony_score = (
            (in_chord / len(decoded_notes)) * 0.7 +
            (in_scale / len(decoded_notes)) * 0.3
        )
    else:
        harmony_score = 0.3  # Rests are somewhat acceptable

    # 2. RHYTHMIC FIT
    beat_strength = BEAT_WEIGHTS[beat_position]
    has_note = len(decoded_notes) > 0

    if has_note and beat_strength >= 0.7:
        rhythm_score = 1.0          # Note on a strong beat
    elif not has_note and beat_strength < 0.4:
        rhythm_score = 0.8          # Rest on a weak beat
    elif has_note and beat_strength < 0.3:
        rhythm_score = 0.3          # Note on a very weak beat
    elif not has_note and beat_strength >= 0.7:
        rhythm_score = 0.4          # Rest on a strong beat (missed opportunity)
    else:
        rhythm_score = 0.5

    # 3. DYNAMIC RANGE
    if 20 < velocity < 110:
        dynamics_score = 1.0
    elif velocity == 0:
        dynamics_score = 0.2
    else:
        dynamics_score = 0.5

    return (harmony_score * harmony_weight +
            rhythm_score * rhythm_weight +
            dynamics_score * dynamics_weight)


class CoherenceTracker:
    """Tracks coherence over time with exponential moving average."""

    def __init__(self, smoothing=0.1):
        self.smoothing = smoothing
        self.current = 0.5
        self.history = []

    def update(self, raw_score):
        """Update the running coherence score."""
        self.current = (self.smoothing * raw_score +
                       (1 - self.smoothing) * self.current)
        self.history.append(self.current)
        return self.current

    def trend(self, window=64):
        """Return the trend over the last `window` values. Positive = improving."""
        if len(self.history) < window:
            return 0.0
        recent = self.history[-window:]
        first_half = sum(recent[:window // 2]) / (window // 2)
        second_half = sum(recent[window // 2:]) / (window // 2)
        return second_half - first_half
