"""Decoder — converts spike patterns from output zones into musical events.

Each 16th-note window, we accumulate spikes from the pitch, velocity, and
timing zones, then decode them into MIDI-ready note events.
"""

from .channels import PITCH_CHANNELS, VELOCITY_CHANNELS, TIMING_CHANNELS


class DecodedEvent:
    """A decoded musical event from one 16th-note window."""

    __slots__ = ('notes', 'velocity', 'timing_offset_ms')

    def __init__(self, notes, velocity, timing_offset_ms):
        self.notes = notes                    # list[int] — pitch classes (0–11)
        self.velocity = velocity              # int — MIDI velocity (0–127)
        self.timing_offset_ms = timing_offset_ms  # float — offset from window center


class Decoder:
    """Decodes accumulated spikes into musical events."""

    def __init__(self, spike_threshold=3, max_velocity_spikes=50):
        self.spike_threshold = spike_threshold
        self.max_velocity_spikes = max_velocity_spikes

    def decode(self, spikes, window_start_ts=0, window_duration_ms=125):
        """Decode a list of Spike objects into a DecodedEvent.

        Args:
            spikes: list of cl.Spike from one 16th-note window
            window_start_ts: timestamp of window start (for timing calc)
            window_duration_ms: window duration in ms

        Returns:
            DecodedEvent with notes, velocity, and timing offset
        """
        pitch_counts = [0] * 12
        velocity_count = 0
        timing_timestamps = []

        for spike in spikes:
            ch = spike.channel

            if ch in PITCH_CHANNELS:
                idx = PITCH_CHANNELS.index(ch)
                pitch_counts[idx] += 1

            elif ch in VELOCITY_CHANNELS:
                velocity_count += 1

            elif ch in TIMING_CHANNELS:
                timing_timestamps.append(spike.timestamp)

        # Pitch: channels above threshold fire notes
        notes = [i for i, count in enumerate(pitch_counts)
                 if count >= self.spike_threshold]

        # Velocity: spike density scaled to MIDI range
        normalized = min(velocity_count / self.max_velocity_spikes, 1.0)
        velocity = int(normalized * 127)

        # Timing: average offset from window center
        timing_offset_ms = 0.0
        if timing_timestamps:
            avg_ts = sum(timing_timestamps) / len(timing_timestamps)
            center = window_start_ts + (window_duration_ms / 2)
            timing_offset_ms = avg_ts - center

        return DecodedEvent(notes, velocity, timing_offset_ms)
