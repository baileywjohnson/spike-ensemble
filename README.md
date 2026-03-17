# Spike Ensemble

A closed-loop system where living neurons on a [Cortical Labs CL1](https://corticallabs.com) MEA produce real-time generative music. Built on the [CL SDK](https://github.com/Cortical-Labs/cl-sdk).

Musical context (rhythm, harmony, dynamics) is encoded as electrical stimulation. Neural spike output is decoded into notes. A coherence scoring system provides feedback to shape the neurons toward musicality over time.

## How It Works

The CL1 chip has a grid of 64 electrodes under a layer of biological neurons. Spike Ensemble partitions these into input and output zones:

**Input (stimulation):**
- **Rhythm** — beat position encoded as pulse intensity
- **Harmony** — chord tones mapped to electrode groups
- **Dynamics** — energy level encoded as channel count
- **Feedback** — coherence reward/punishment signal

**Output (spike readout):**
- **Pitch** — 12 channels mapping to chromatic notes (C through B)
- **Velocity** — spike density across channels maps to loudness
- **Timing** — spike onset within beat windows maps to micro-timing

A coherence score (harmonic fit + rhythmic fit + dynamics) drives the feedback loop. High coherence produces a clean reward pulse; low coherence produces noisy random stimulation. Over time, the neurons should learn to minimize surprise and produce more musical output.

## Setup

### Prerequisites

- Python 3.12+
- [CL SDK](https://docs.corticallabs.com/) (`cl-sdk-main/` directory, not included in repo)

### Install

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install the CL SDK
pip install -e cl-sdk-main/

# Install remaining dependencies
pip install python-dotenv
```

### Configure

Create a `.env` file in the project root:

```bash
# For the real CL1:
CL_SDK_ACCELERATED_TIME=0
CL_SDK_WEBSOCKET=1
CL_SDK_WEBSOCKET_PORT=1025
```

See the [CL SDK docs](https://docs.corticallabs.com/) for authentication and connection configuration.

#### Simulator mode

To run locally without hardware, add a replay file path:

```bash
CL_SDK_REPLAY_PATH=./data/your_recording.h5
CL_SDK_REPLAY_START_OFFSET=0
CL_SDK_RANDOM_SEED=42
```

## Usage

There are three ways to run Spike Ensemble:

### 1. Demo mode (no hardware or SDK needed)

Open the [live demo](https://baileywjohnson.github.io/spike-ensemble/) or open `web/standalone.html` in a browser with `?demo` in the URL. Click **Start** to run a simulated performance with audio. This uses generated neural activity to demonstrate the system.

### 2. Web server + simulator

Start the server, then control the simulation from the browser:

```bash
python server.py
```

Open [http://localhost:8080](http://localhost:8080) and click **Start**. The server spawns `run.py` as a subprocess and the browser connects to the CL SDK's WebSocket for live data. Use `--port` to change the HTTP port.

This requires the CL SDK installed and a `.env` configured (see [Configure](#configure)). For local testing without a CL1, use simulator mode with a replay file.

### 3. Direct CLI

Run the simulation directly from the terminal:

```bash
python run.py
```

Then open `web/standalone.html` in a browser to see the visualization. The page connects via WebSocket to `ws://127.0.0.1:1025` by default.

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--bpm` | 120 | Beats per minute |
| `--duration` | 600 | Session length in seconds |
| `--threshold` | 3 | Min spikes per channel to trigger a note |
| `--octave` | 4 | MIDI octave for output |

Example:

```bash
python run.py --bpm 90 --duration 300 --threshold 2
```

### Browser dashboard

The web UI shows:

- **MEA heatmap** — real-time stimulation and spike activity across the 8x8 electrode grid
- **Piano roll** — decoded note output over time
- **Coherence graph** — tracks how "musical" the output is

URL parameters for the web UI:

| Param | Example | Description |
|-------|---------|-------------|
| `demo` | `?demo` | Force demo mode (no backend needed) |
| `server` | `?server=http://localhost:8080` | Backend server URL for live mode |
| `port` | `?port=1025` | CL SDK WebSocket port |
| `host` | `?host=127.0.0.1` | CL SDK WebSocket host |

When opened on localhost, the page defaults to live mode (connecting to the backend). When hosted elsewhere (e.g. GitHub Pages), it defaults to demo mode.

## Performance Phases

| Phase | Default Start | Description |
|-------|--------------|-------------|
| Listening | 0s | Neurons receive context stimulation, no decoding |
| First Notes | 5s | Decoding begins, expect noise, gentle feedback |
| Learning | 30s | Feedback intensifies, coherence should climb |
| Jamming | 120s | Reduced feedback, neurons express what they learned |
| Challenge | 300s | Key/tempo changes test generalization |

## Project Structure

```
src/
  channels.py    — MEA electrode layout and zone partitioning
  sequencer.py   — Musical state and stimulation pattern encoding
  decoder.py     — Spike-to-note decoding
  coherence.py   — Coherence scoring and tracking
  midi_output.py — MIDI output (optional, falls back to console)
  main.py        — Main closed-loop runner
web/
  standalone.html — Browser visualization, Web Audio synth, and demo mode
server.py        — HTTP server with API to start/stop simulations
run.py           — CLI entry point
```

## Chord Progression

The default progression is **I-vi-IV-V in C major**:

```
Cmaj (C E G) -> Amin (A C E) -> Fmaj (F A C) -> Gmaj (G B D)
```

Each chord lasts one bar. Pass a custom progression via the `chord_progression` parameter in `run()`.
