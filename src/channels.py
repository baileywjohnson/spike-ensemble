"""MEA channel layout and partitioning for Spike Ensemble.

The CL1 MEA is an 8x8 grid of 64 electrodes. Corners (0, 7, 56, 63)
are inactive references, leaving 60 usable channels partitioned into
input (stimulation) and output (spike readout) zones.
"""

from cl import ChannelSet

# Reference electrodes (inactive)
REF_CHANNELS = [0, 7, 56, 63]

# ── Input Zones (Stimulation) ──

# Rhythm: beat position encoding (top-left region)
RHYTHM_CHANNELS = [1, 2, 3, 8, 9, 10, 11]

# Harmony: chord/scale tone encoding (left-middle region)
HARMONY_CHANNELS = [16, 17, 18, 19, 24, 25, 26, 27, 32, 33]

# Dynamics: energy level / volume encoding (bottom-left region)
DYNAMICS_CHANNELS = [34, 35, 40, 41, 42, 43, 48, 49, 50, 51, 57, 58]

# Feedback: single coherence feedback channel
FEEDBACK_CHANNEL = 59

# ── Output Zones (Spike Readout) ──

# Pitch: 12 channels = 12 chromatic pitch classes (C through B)
PITCH_CHANNELS = [4, 5, 6, 12, 13, 14, 20, 21, 28, 29, 36, 37]

# Velocity: spike density across these channels → loudness
VELOCITY_CHANNELS = [44, 45, 46, 47, 52, 53, 54, 55, 30, 31, 38]

# Timing: spike onset timing within the beat window → micro-timing/swing
TIMING_CHANNELS = [39, 60, 61, 62, 22, 15, 23]

# ── Pitch class names for display ──
PITCH_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# ── Channel sets for bulk operations ──
ALL_INPUT_CHANNELS = ChannelSet(
    *RHYTHM_CHANNELS, *HARMONY_CHANNELS, *DYNAMICS_CHANNELS, FEEDBACK_CHANNEL
)
ALL_OUTPUT_CHANNELS = ChannelSet(
    *PITCH_CHANNELS, *VELOCITY_CHANNELS, *TIMING_CHANNELS
)
