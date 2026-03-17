"""MIDI output — sends decoded neural events as MIDI messages.

Supports both external MIDI output (via mido/rtmidi) and a fallback
console logger for development without MIDI hardware.
"""

import threading


def pitch_class_to_midi(pitch_class, octave=4):
    """Convert pitch class (0–11) to MIDI note number."""
    return 12 * (octave + 1) + pitch_class


class MidiOutput:
    """Sends MIDI note events to an output port."""

    def __init__(self, port_name=None, default_octave=4, note_duration_s=0.1):
        self.default_octave = default_octave
        self.note_duration_s = note_duration_s
        self._port = None
        self._mido = None
        self._active_notes = set()

        try:
            import mido
            self._mido = mido
            if port_name:
                self._port = mido.open_output(port_name)
            else:
                # Try to open default output
                available = mido.get_output_names()
                if available:
                    self._port = mido.open_output(available[0])
                    print(f"MIDI output: {available[0]}")
                else:
                    print("No MIDI output ports available — using console output")
        except (ImportError, Exception) as e:
            print(f"MIDI not available ({e}) — using console output")

    def send_note(self, pitch_class, velocity, timing_offset_ms=0, octave=None):
        """Send a MIDI note-on, auto note-off after duration."""
        if octave is None:
            octave = self.default_octave

        midi_note = pitch_class_to_midi(pitch_class, octave)

        if velocity <= 0:
            return

        if self._port and self._mido:
            msg_on = self._mido.Message(
                'note_on', note=midi_note, velocity=velocity, channel=0
            )
            self._port.send(msg_on)
            self._active_notes.add(midi_note)

            # Schedule note-off
            def note_off():
                msg_off = self._mido.Message(
                    'note_off', note=midi_note, velocity=0, channel=0
                )
                if self._port:
                    self._port.send(msg_off)
                self._active_notes.discard(midi_note)

            timer = threading.Timer(self.note_duration_s, note_off)
            timer.daemon = True
            timer.start()

    def send_event(self, decoded_event, octave=None):
        """Send all notes from a DecodedEvent."""
        for pitch_class in decoded_event.notes:
            self.send_note(
                pitch_class,
                decoded_event.velocity,
                decoded_event.timing_offset_ms,
                octave,
            )

    def all_notes_off(self):
        """Send note-off for all active notes."""
        if self._port and self._mido:
            for note in list(self._active_notes):
                msg = self._mido.Message(
                    'note_off', note=note, velocity=0, channel=0
                )
                self._port.send(msg)
            self._active_notes.clear()

    def close(self):
        """Clean up MIDI resources."""
        self.all_notes_off()
        if self._port:
            self._port.close()
            self._port = None
