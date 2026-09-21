from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sherpa_onnx

from odoo.libs.documents import Cue

from odoo.addons.media.tools.audio import SAMPLE_RATE

ENCODER = "encoder.onnx"
DECODER = "decoder.onnx"
TOKENS = "tokens.txt"
VAD = "vad.onnx"
SEGMENTATION = "segmentation.onnx"
EMBEDDING = "embedding.onnx"
REQUIRED = (ENCODER, DECODER, TOKENS, VAD)

MAX_UTTERANCE_S = 20.0
MIN_SILENCE_S = 0.5
CLUSTER_THRESHOLD = 0.5


def num_threads() -> int:
    return max(1, min(4, (os.cpu_count() or 2) // 2))


def whisper_language(language: str | None) -> str:
    return (language or "").replace("-", "_").split("_")[0].lower()


@dataclass(frozen=True)
class Utterance:
    start: float
    end: float
    samples: np.ndarray


class LocalEngine:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self._recognizers: dict[str, sherpa_onnx.OfflineRecognizer] = {}
        self._diarizer: sherpa_onnx.OfflineSpeakerDiarization | None = None
        self._lock = threading.Lock()

    @classmethod
    def missing_files(cls, model_dir: Path) -> list[str]:
        return [name for name in REQUIRED if not (model_dir / name).is_file()]

    @property
    def diarizes(self) -> bool:
        return all(
            (self.model_dir / name).is_file() for name in (SEGMENTATION, EMBEDDING)
        )

    def transcribe(self, samples: np.ndarray, language: str | None = None) -> list[Cue]:
        with self._lock:
            utterances = self._utterances(samples)
            if not utterances:
                return []
            texts = self._recognize(utterances, whisper_language(language))
            turns = self._turns(samples) if self.diarizes else []
        return [
            Cue(
                start=round(utterance.start, 2),
                end=round(utterance.end, 2),
                text=text,
                speaker=speaker_of(utterance, turns),
            )
            for utterance, text in zip(utterances, texts, strict=True)
            if text
        ]

    def _utterances(self, samples: np.ndarray) -> list[Utterance]:
        config = sherpa_onnx.VadModelConfig()
        config.silero_vad.model = str(self.model_dir / VAD)
        config.silero_vad.min_silence_duration = MIN_SILENCE_S
        config.silero_vad.max_speech_duration = MAX_UTTERANCE_S
        config.sample_rate = SAMPLE_RATE
        config.num_threads = 1
        buffer_s = samples.size / SAMPLE_RATE + MAX_UTTERANCE_S
        vad = sherpa_onnx.VoiceActivityDetector(config, buffer_size_in_seconds=buffer_s)
        window = config.silero_vad.window_size
        utterances = []
        for offset in range(0, samples.size, window):
            vad.accept_waveform(samples[offset : offset + window])
            utterances.extend(self._drain(vad))
        vad.flush()
        utterances.extend(self._drain(vad))
        return utterances

    def _drain(self, vad: sherpa_onnx.VoiceActivityDetector) -> list[Utterance]:
        found = []
        while not vad.empty():
            segment = vad.front
            samples = np.asarray(segment.samples, dtype=np.float32)
            start = segment.start / SAMPLE_RATE
            found.append(Utterance(start, start + samples.size / SAMPLE_RATE, samples))
            vad.pop()
        return found

    def _recognize(self, utterances: list[Utterance], language: str) -> list[str]:
        recognizer = self._recognizer(language)
        streams = []
        for utterance in utterances:
            stream = recognizer.create_stream()
            stream.accept_waveform(SAMPLE_RATE, utterance.samples)
            streams.append(stream)
        recognizer.decode_streams(streams)
        return [stream.result.text.strip() for stream in streams]

    def _recognizer(self, language: str) -> sherpa_onnx.OfflineRecognizer:
        if language not in self._recognizers:
            self._recognizers[language] = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=str(self.model_dir / ENCODER),
                decoder=str(self.model_dir / DECODER),
                tokens=str(self.model_dir / TOKENS),
                language=language,
                task="transcribe",
                num_threads=num_threads(),
            )
        return self._recognizers[language]

    def _turns(self, samples: np.ndarray) -> list[tuple[float, float, int]]:
        if self._diarizer is None:
            config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
                segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                    pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                        model=str(self.model_dir / SEGMENTATION)
                    ),
                    num_threads=num_threads(),
                ),
                embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(
                    model=str(self.model_dir / EMBEDDING),
                    num_threads=num_threads(),
                ),
                clustering=sherpa_onnx.FastClusteringConfig(
                    num_clusters=-1, threshold=CLUSTER_THRESHOLD
                ),
                min_duration_on=0.3,
                min_duration_off=MIN_SILENCE_S,
            )
            if not config.validate():
                raise ValueError(
                    f"The speaker models in {self.model_dir} cannot be loaded"
                )
            self._diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)
        result = self._diarizer.process(samples).sort_by_start_time()
        return [(turn.start, turn.end, turn.speaker) for turn in result]


def speaker_of(utterance: Utterance, turns: list[tuple[float, float, int]]) -> str:
    overlap: dict[int, float] = {}
    for start, end, speaker in turns:
        shared = min(end, utterance.end) - max(start, utterance.start)
        if shared > 0:
            overlap[speaker] = overlap.get(speaker, 0.0) + shared
    if not overlap:
        return ""
    return f"SPEAKER_{max(overlap, key=overlap.__getitem__)}"
