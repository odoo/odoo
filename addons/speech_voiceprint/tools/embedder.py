import math

import numpy as np

from odoo.addons.media.tools.audio import SAMPLE_RATE


def slice_spans(samples, spans, max_seconds=60.0, sample_rate=SAMPLE_RATE):
    ordered = sorted(spans, key=lambda s: s[1] - s[0], reverse=True)
    parts, total = [], 0.0
    for start, end in ordered:
        if total >= max_seconds:
            break
        a, b = int(start * sample_rate), int(end * sample_rate)
        piece = samples[max(a, 0) : max(b, 0)]
        if piece.size:
            parts.append(piece)
            total += piece.size / sample_rate
    if not parts:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(parts)


class SpeakerEmbedder:
    def __init__(self, model_path, num_threads=2):
        import sherpa_onnx

        config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=model_path, num_threads=num_threads
        )
        if not config.validate():
            raise ValueError(f"Speaker model not usable: {model_path}")
        self._extractor = sherpa_onnx.SpeakerEmbeddingExtractor(config)
        self.dim = self._extractor.dim

    def embed(self, samples, sample_rate=SAMPLE_RATE):
        if samples.size < sample_rate:
            return None
        stream = self._extractor.create_stream()
        stream.accept_waveform(sample_rate=sample_rate, waveform=samples)
        stream.input_finished()
        if not self._extractor.is_ready(stream):
            return None
        vector = np.asarray(self._extractor.compute(stream), dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        return (vector / norm).tolist() if norm else None


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0
    num = sum(x * y for x, y in zip(a, b, strict=True))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0
