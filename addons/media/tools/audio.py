import io

import numpy as np

SAMPLE_RATE = 16000


def decode_audio(data, sample_rate=SAMPLE_RATE):
    import av

    chunks = []
    with av.open(io.BytesIO(data)) as container:
        stream = next(s for s in container.streams if s.type == "audio")
        resampler = av.AudioResampler(format="flt", layout="mono", rate=sample_rate)
        for frame in container.decode(stream):
            chunks.extend(
                out.to_ndarray().reshape(-1) for out in resampler.resample(frame)
            )
        chunks.extend(out.to_ndarray().reshape(-1) for out in resampler.resample(None))
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(chunks).astype(np.float32)
