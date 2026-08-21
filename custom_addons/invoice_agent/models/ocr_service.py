"""OCR service — the only module that touches Tesseract / poppler.

Service contract:

* ``_extract_text(attachment)`` decodes ``attachment.datas`` (base64),
  branches on ``mimetype`` and runs the rasterize -> Tesseract pipeline:
    - ``application/pdf`` : ``pdf2image.convert_from_bytes(raw, dpi=300)``
      renders each page at 300 DPI (the DPI that consistently beats 150 in
      the benchmark — see docs/adr-002-ocr-engine.md), then
      ``pytesseract.image_to_data(...)`` extracts both the text and the
      per-word ``conf`` array in a single OCR pass.
    - ``image/*``         : PIL can read the frame directly, same OCR pass.
  Returns ``{"text": ..., "confidence": <mean word confidence 0..1>}``.
* Guards, in order: no data -> raise; over 20 MB -> raise; non-PDF/non-image
  mimetype -> raise; zero-page PDF -> raise. A rejected upload must fail
  loudly enough for the cron to mark the move ``ocr_state='failed'`` with a
  message an accountant can read, never silently return empty text.
* Import safety mirrors ``invoice_extraction.py``: on a stale image without
  ``pytesseract``/``pdf2image``/the tesseract binary the module still loads;
  the first real call raises a clear ``UserError`` telling the operator to
  rebuild the image with ``docker compose build odoo``.

Why this lives in its own AbstractModel instead of on ``account.move``:
the twenty-second OCR job is consumed by an ``ir.cron`` worker, and the
attachment-only interface keeps a clean seam so the cron can be replaced by
a real queue worker without touching the model.
"""

import base64
import io
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Anything over 20 MB is rejected before poppler is invoked — a 20 MB scan
# is already an anomaly, and rasterizing a monster PDF would pin a worker
# for minutes. Arbitrary but documented; the ADR quotes it.
MAX_OCR_ATTACHMENT_BYTES = 20 * 1024 * 1024

# pdf2image render DPI. 300 DPI is the measured sweet spot from the OCR
# benchmark (scripts/bench_ocr.py): at 150 DPI accuracy drops ~2-3 points on
# the degraded scans; above 300 DPI latency grows linearly with no accuracy
# gain on printed invoices.
OCR_RENDER_DPI = 300

# Tesseract PSM chosen by the benchmark: --psm 6 (treat the image as a
# single uniform block of text) beats --psm 11 (sparse text) on full-page
# invoice scans by a wide margin on both accuracy and confidence.
OCR_PSM = 6
OCR_OEM = 3


class InvoiceOcrService(models.AbstractModel):
    _name = "invoice.ocr.service"
    _description = "OCR engine wrapper (Tesseract + poppler via pdf2image)"

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    @api.model
    def _extract_text(self, attachment):
        """Return ``{"text": str, "confidence": float}`` for one attachment.

        :raises UserError: with an accountant-readable message for every
            guard failure — no data, over 20 MB, unsupported mimetype,
            zero-page PDF, or a stale image missing the OCR toolchain.
        """
        if not attachment:
            raise UserError(_("No attachment to OCR."))
        datas = attachment.datas
        if not datas:
            raise UserError(
                _("Attachment '%s' has no data — it cannot be OCR'd.", attachment.name),
            )

        raw = base64.b64decode(datas)
        if len(raw) > MAX_OCR_ATTACHMENT_BYTES:
            raise UserError(
                _(
                    "Attachment '%s' is %.1f MB — over the 20 MB OCR limit.",
                    attachment.name,
                    len(raw) / (1024 * 1024),
                ),
            )

        mimetype = attachment.mimetype or "application/octet-stream"
        if mimetype == "application/pdf":
            return self._extract_pdf(raw, attachment.name)
        if mimetype.startswith("image/"):
            return self._extract_image(raw, attachment.name)
        raise UserError(
            _(
                "Attachment '%s' is type '%s' — only PDF and image files can be OCR'd.",
                attachment.name,
                mimetype,
            ),
        )

    # ------------------------------------------------------------------
    # Mimetype branches
    # ------------------------------------------------------------------
    def _extract_pdf(self, raw, name):
        """Rasterize a PDF at 300 DPI and OCR every page."""
        from pdf2image import convert_from_bytes

        self._check_toolchain()
        try:
            images = convert_from_bytes(raw, dpi=OCR_RENDER_DPI)
        except Exception as exc:
            raise UserError(
                _("Could not rasterize PDF '%s': %s", name, exc),
            ) from exc
        if not images:
            raise UserError(_("PDF '%s' has no pages to OCR.", name))
        return self._ocr_images(images)

    def _extract_image(self, raw, name):
        """OCR a single raster image directly (no pdf2image step)."""
        from PIL import Image

        self._check_toolchain()
        try:
            image = Image.open(io.BytesIO(raw))
            image.load()
        except Exception as exc:
            raise UserError(
                _("Could not read image '%s': %s", name, exc),
            ) from exc
        return self._ocr_images([image])

    # ------------------------------------------------------------------
    # Shared OCR pass
    # ------------------------------------------------------------------
    def _ocr_images(self, images):
        """Run one Tesseract pass per page; return text and mean confidence.

        ``pytesseract.image_to_data`` yields the per-word ``conf`` array
        (0-100, -1 for non-word rows) in the same pass as the text, so the
        confidence is measured on the exact tokens that produced the output.
        """
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
            # Zero readable text is a real signal — the scan is blank or the
            # page is a photograph. Surface it as a failure, not a "success"
            # with an empty string that would poison LLM extraction later.
            raise UserError(
                _(
                    "OCR produced no text — the document is blank, the scan "
                    "is too dark, or it is not a text document.",
                ),
            )
        return {
            "text": text,
            "confidence": sum(confs) / len(confs) if confs else 0.0,
        }

    # ------------------------------------------------------------------
    # Toolchain presence check
    # ------------------------------------------------------------------
    def _check_toolchain(self):
        """Raise a clear error when the OCR stack is missing from the image."""
        import shutil

        try:
            import pdf2image  # noqa: F401
            import pytesseract  # noqa: F401
        except ImportError as exc:
            raise UserError(
                _(
                    "The OCR Python packages are not installed in this image. "
                    "Rebuild it with `docker compose build odoo`.",
                ),
            ) from exc
        if shutil.which("tesseract") is None:
            raise UserError(
                _(
                    "The tesseract binary is not installed in this image. "
                    "Rebuild it with `docker compose build odoo`.",
                ),
            )
        if shutil.which("pdftoppm") is None and shutil.which("pdfinfo") is None:
            # pdf2image uses pdftoppm (poppler-utils); pdfinfo is a sibling
            # binary from the same package — either present means poppler is
            # installed.
            raise UserError(
                _(
                    "poppler-utils is not installed in this image — PDF "
                    "rasterization is unavailable. Rebuild it with "
                    "`docker compose build odoo`.",
                ),
            )
