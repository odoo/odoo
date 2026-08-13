"""OCR — the only module that touches Tesseract / poppler.

Ported from ``custom_addons/invoice_agent/models/ocr_service.py`` (ADR-002:
Tesseract psm 6 @ 300 DPI). Contract unchanged:

* ``extract_bytes(raw, mimetype, filename)`` branches on mimetype:
    - ``application/pdf``: ``pdf2image.convert_from_bytes(raw, dpi=300)``
      renders each page, then ``pytesseract.image_to_data`` extracts text +
      per-word confidence in one pass.
    - ``image/*``: PIL reads the frame directly, same OCR pass.
  Returns ``{"text": ..., "confidence": <mean word confidence 0..1>}``.
* Guards in order: empty input -> BadRequestError; >20 MB ->
  UploadTooLargeError (service limit — the HTTP layer enforces 10 MiB
  earlier per OpenAPI); unsupported mimetype -> UnsupportedMediaTypeError;
  zero-page PDF -> BadRequestError; zero readable text -> BadRequestError
  (a blank scan must fail loudly, never extract garbage).
"""

import io
import logging
from typing import Any

from .errors import BadRequestError, UnsupportedMediaTypeError, UploadTooLargeError

_logger = logging.getLogger(__name__)

MAX_OCR_BYTES = 20 * 1024 * 1024
OCR_RENDER_DPI = 300
OCR_PSM = 6
OCR_OEM = 3

ALLOWED_MIMETYPES = ("application/pdf", "image/png", "image/jpeg", "image/tiff")


def extract_bytes(raw: bytes, mimetype: str, filename: str = "") -> dict[str, Any]:
    """Return ``{"text": str, "confidence": float}`` for raw document bytes."""
    if not raw:
        raise BadRequestError("No document bytes to OCR.")
    if len(raw) > MAX_OCR_BYTES:
        raise UploadTooLargeError(
            f"Document is {len(raw) / (1024 * 1024):.1f} MiB — over the "
            f"{MAX_OCR_BYTES // (1024 * 1024)} MiB OCR limit.",
        )
    if mimetype not in ALLOWED_MIMETYPES:
        raise UnsupportedMediaTypeError(
            f"Unsupported mimetype '{mimetype}'. Allowed: {', '.join(ALLOWED_MIMETYPES)}",
        )

    if mimetype == "application/pdf":
        images = _rasterize_pdf(raw, filename)
    else:
        images = [_read_image(raw, filename)]

    return _ocr_images(images)


def _rasterize_pdf(raw: bytes, filename: str) -> list[Any]:
    from pdf2image import convert_from_bytes

    try:
        images = convert_from_bytes(raw, dpi=OCR_RENDER_DPI)
    except Exception as exc:
        raise BadRequestError(f"Could not rasterize PDF '{filename}': {exc}") from exc
    if not images:
        raise BadRequestError(f"PDF '{filename}' has no pages to OCR.")
    return images


def _read_image(raw: bytes, filename: str) -> Any:
    from PIL import Image

    try:
        image = Image.open(io.BytesIO(raw))
        image.load()
        return image
    except Exception as exc:
        raise BadRequestError(f"Could not read image '{filename}': {exc}") from exc


def _ocr_images(images: list[Any]) -> dict[str, Any]:
    import pytesseract

    text_parts = []
    confs = []
    for image in images:
        data = pytesseract.image_to_data(
            image,
            config=f"--psm {OCR_PSM} --oem {OCR_OEM}",
            output_type=pytesseract.Output.DICT,
        )
        words = data.get("text") or []
        conf = data.get("conf") or []
        line_words = []
        for index, word in enumerate(words):
            if not (word or "").strip():
                continue
            value = conf[index] if index < len(conf) else -1
            if value >= 0:
                confs.append(value / 100.0)
            line_words.append(word)
        text_parts.append(" ".join(line_words))

    text = "\n".join(part for part in text_parts if part.strip())
    if not text.strip():
        raise BadRequestError(
            "OCR produced no text — the document is blank, too dark, or not "
            "a text document.",
        )
    return {
        "text": text,
        "confidence": sum(confs) / len(confs) if confs else 0.0,
    }
