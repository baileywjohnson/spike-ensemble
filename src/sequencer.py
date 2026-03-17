"""Sequencer — encodes musical context as stimulation patterns.

Drives the musical timeline: beat position, chord progression, dynamics.
Converts musical state into electrical stimulation delivered to the neurons.
"""

import random

from cl import ChannelSet, StimDesign, BurstDesign

from .channels import (
    RHYTHM_CHANNELS, HARMONY_CHANNELS, DYNAMICS_CHANNELS, FEEDBACK_CHANNEL,
)

# ── Beat weights: how "strong" each 16th-note position is ──
BEAT_WEIGHTS = {
    0: 1.0,   1: 0.2,  2: 0.4,  3: 0.2,   # Beat 1
    4: 0.7,   5: 0.2,  6: 0.4,  7: 0.2,   # Beat 2
    8: 1.0,   9: 0.2, 10: 0.4, 11: 0.2,   # Beat 3
    12: 0.7, 13: 0.2, 14: 0.4, 15: 0.2,   # Beat 4
}

# ── Stim designs by beat strength ──
STRONG_STIM = StimDesign(160, -2.0, 160, 2.0)   # Downbeats
MEDIUM_STIM = StimDesign(160, -1.5, 160, 1.5)   # Backbeats
WEAK_STIM   = StimDesign(160, -1.0, 160, 1.0)   # 8th notes
GHOST_STIM  = StimDesign(160, -0.5, 160, 0.5)   # 16th subdivisions

# ── Harmony channel mapping (pitch class → harmony channels) ──
# Root and fifth get doubled representation for stronger encoding
HARMONY_MAP = {
    0:  [0, 1],    # C  (root) → H0, H1
    2:  [2],       # D
    4:  [3],       # E
    5:  [4],       # F
    7:  [5, 6],    # G  (fifth) → H5, H6
    9:  [7],       # A
    11: [8],       # B
    # Chromatic tones share channels
    1:  [9],       # C#
    3:  [2],       # D# (shares with D)
    6:  [4],       # F# (shares with F)
    8:  [9],       # G# (shares with C#)
    10: [7],       # A# (shares with A)
}

HARMONY_STIM = StimDesign(200, -1.5, 200, 1.5)

# ── Dynamics levels (channel count = energy) ──
DYNAMICS_LEVELS = {
    0: [],
    1: [0, 1, 2],
    2: [0, 1, 2, 3, 4, 5],
    3: [0, 1, 2, 3, 4, 5, 6, 7, 8],
    4: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
}

DYNAMICS_STIM = StimDesign(160, -1.2, 160, 1.2)

# ── Feedback stim designs ──
REWARD_STIM = StimDesign(200, -2.0, 200, 2.0)
NOISE_STIM_BASE_DURATION = 120


class Sequencer:
    """Manages musical state and delivers stimulation to the neurons."""

    def __init__(self, bpm=120, chord_progression=None):
        self.bpm = bpm
        self.beat_duration_ms = 60_000 / bpm
        self.subdivision_duration_ms = self.beat_duration_ms / 4  # 16th notes
        self.ticks_per_subdivision = int(self.subdivision_duration_ms)

        self.bar_position = 0       # 0–15 (16th-note position)
        self.chord_index = 0
        self.bars_elapsed = 0

        self.chord_progression = chord_progression or [
            ('Cmaj', [0, 4, 7]),     # C E G
            ('Amin', [9, 0, 4]),     # A C E
            ('Fmaj', [5, 9, 0]),     # F A C
            ('Gmaj', [7, 11, 2]),    # G B D
        ]

    @property
    def current_chord(self):
        return self.chord_progression[self.chord_index]

    @property
    def current_chord_name(self):
        return self.current_chord[0]

    @property
    def current_chord_tones(self):
        return self.current_chord[1]

    @property
    def beat_weight(self):
        return BEAT_WEIGHTS[self.bar_position]

    def get_dynamics_level(self):
        """Return dynamics level 0–4 based on bar position and arrangement."""
        # Simple crescendo pattern within each bar
        if self.bar_position < 4:
            return 2
        elif self.bar_position < 8:
            return 3
        elif self.bar_position < 12:
            return 3
        else:
            return 2

    def advance(self):
        """Advance to the next 16th-note position. Returns True on new bar."""
        self.bar_position = (self.bar_position + 1) % 16
        if self.bar_position == 0:
            self.chord_index = (self.chord_index + 1) % len(self.chord_progression)
            self.bars_elapsed += 1
            return True
        return False

    def deliver_rhythm_stim(self, neurons):
        """Stimulate rhythm channels based on current beat position."""
        weight = self.beat_weight

        if weight >= 1.0:
            stim = STRONG_STIM
            channels = RHYTHM_CHANNELS
        elif weight >= 0.7:
            stim = MEDIUM_STIM
            channels = RHYTHM_CHANNELS[:4]
        elif weight >= 0.4:
            stim = WEAK_STIM
            channels = [RHYTHM_CHANNELS[self.bar_position % len(RHYTHM_CHANNELS)]]
        else:
            stim = GHOST_STIM
            channels = [RHYTHM_CHANNELS[self.bar_position % len(RHYTHM_CHANNELS)]]

        neurons.stim(ChannelSet(*channels), stim)

    def deliver_harmony_stim(self, neurons):
        """Stimulate harmony channels for current chord tones."""
        active_indices = []
        for tone in self.current_chord_tones:
            if tone in HARMONY_MAP:
                active_indices.extend(HARMONY_MAP[tone])

        active_channels = [HARMONY_CHANNELS[i] for i in set(active_indices)
                          if i < len(HARMONY_CHANNELS)]

        if active_channels:
            neurons.stim(ChannelSet(*active_channels), HARMONY_STIM)

    def deliver_dynamics_stim(self, neurons):
        """Stimulate dynamics channels based on current energy level."""
        level = self.get_dynamics_level()
        indices = DYNAMICS_LEVELS[level]

        if indices:
            channels = [DYNAMICS_CHANNELS[i] for i in indices
                       if i < len(DYNAMICS_CHANNELS)]
            if channels:
                neurons.stim(ChannelSet(*channels), DYNAMICS_STIM)

    def deliver_feedback(self, neurons, coherence):
        """Apply coherence-based feedback stimulation.

        High coherence → clean, predictable stim (reward).
        Low coherence → noisy, random stim (punishment).
        """
        if coherence > 0.7:
            neurons.stim(FEEDBACK_CHANNEL, REWARD_STIM)
        elif coherence < 0.3:
            # Noisy random stim across many channels
            noise_channels = random.sample(range(64), k=20)
            duration = random.choice([80, 120, 160])
            current = random.uniform(0.5, 2.0)
            noise_stim = StimDesign(duration, -current, duration, current)
            neurons.stim(ChannelSet(*noise_channels), noise_stim)
        else:
            # Moderate feedback — mild pulse on feedback channel
            mild_stim = StimDesign(160, -1.0, 160, 1.0)
            neurons.stim(FEEDBACK_CHANNEL, mild_stim)

    def deliver_all(self, neurons, coherence=0.5):
        """Deliver all stimulation for the current subdivision."""
        self.deliver_rhythm_stim(neurons)
        self.deliver_harmony_stim(neurons)
        self.deliver_dynamics_stim(neurons)
        self.deliver_feedback(neurons, coherence)
