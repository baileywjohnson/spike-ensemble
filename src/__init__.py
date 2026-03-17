"""Spike Ensemble — Living Neurons That Jam.

CL1 application entry point following the Cortical Labs app framework.
"""

from cl.app import BaseApplication, BaseApplicationConfig, RunSummary, OutputType


class SpikeEnsembleConfig(BaseApplicationConfig):
    """Configuration for Spike Ensemble performance."""
    bpm: int = 120
    spike_threshold: int = 3
    default_octave: int = 4
    duration_seconds: int = 600


class SpikeEnsembleApp(BaseApplication):
    @staticmethod
    def config_class():
        return SpikeEnsembleConfig

    @staticmethod
    def run(config: SpikeEnsembleConfig, output_directory: str):
        from .main import run

        run(
            bpm=config.bpm,
            duration_seconds=config.duration_seconds,
            spike_threshold=config.spike_threshold,
            default_octave=config.default_octave,
        )

        return RunSummary(
            type=OutputType.TEXT,
            content="Spike Ensemble performance complete.",
        )


application = SpikeEnsembleApp()
