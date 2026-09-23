from __future__ import annotations

import logging
from typing import Any

from odoo.libs.documents import (
    IMAGES,
    TEXT,
    BaseReader,
    mimetypes_for,
    register_reader,
)

_logger = logging.getLogger(__name__)

PAGE_BREAK = "\n--PAGE--\n"

RASTER_DPI = 200
RASTER_FALLBACK_DPI = (150, 110, 72)
RASTER_MAX_BYTES = 20 * 1024 * 1024
RASTER_MAX_PAGES = 1

OCR_MIN_CHARS = 8

PDF = mimetypes_for("pdf")
IMAGE_MIMETYPES = mimetypes_for("png", "jpg", "webp", "gif", "bmp")
XML_MIMETYPES = mimetypes_for("xml")
PAGED = PDF | IMAGE_MIMETYPES


def page_count(document: Any) -> int:
    if document.mimetype not in PDF:
        return 1 if document.mimetype in IMAGE_MIMETYPES else 0
    try:
        import pymupdf

        with pymupdf.open(stream=document.data, filetype="pdf") as doc:
            return doc.page_count
    except Exception as e:
        _logger.debug(
            "Could not count pages of %r: %s", document.name, e, exc_info=True
        )
        return 0


def _render(page, name: str) -> bytes:
    dpi = RASTER_DPI
    png = page.get_pixmap(dpi=dpi).tobytes("png")
    for lower in RASTER_FALLBACK_DPI:
        if len(png) <= RASTER_MAX_BYTES:
            break
        _logger.info(
            "%r rendered to %.1f MB at %d dpi, over budget; retrying at %d",
            name,
            len(png) / (1024 * 1024),
            dpi,
            lower,
        )
        dpi = lower
        png = page.get_pixmap(dpi=dpi).tobytes("png")
    return png


class _PdfText(BaseReader):
    name = "pdf_text"
    mimetypes = PDF
    yields = (TEXT,)

    def read(self, document):
        text = ""
        try:
            import pymupdf

            with pymupdf.open(stream=document.data, filetype="pdf") as doc:
                text = PAGE_BREAK.join(page.get_text() for page in doc).strip()
        except Exception as e:
            _logger.debug(
                "Could not read the text layer of %r: %s",
                document.name,
                e,
                exc_info=True,
            )
        # A handful of characters off a whole PDF is a header, not a text layer,
        # and reporting them would end the search before a reader that renders
        # the pages ever ran. Answering nothing is what lets one run.
        return text if len(text) >= OCR_MIN_CHARS else ""


class _XmlText(BaseReader):
    name = "xml_text"
    mimetypes = XML_MIMETYPES
    yields = (TEXT,)

    def read(self, document):
        tree = document.tree
        if tree is None:
            return ""
        return "\n".join(t.strip() for t in tree.itertext() if t.strip())


class _Pages(BaseReader):
    name = "pages"
    mimetypes = PAGED
    yields = (IMAGES,)

    def provides(self, document):
        return document.mimetype in PAGED

    def read(self, document):
        if document.mimetype in IMAGE_MIMETYPES:
            return [document.data]
        try:
            import pymupdf

            with pymupdf.open(stream=document.data, filetype="pdf") as doc:
                if not doc.page_count:
                    return []
                if doc.page_count > RASTER_MAX_PAGES:
                    _logger.warning(
                        "%r has %d pages; rendering the first %d. Pages beyond "
                        "that are not extracted from",
                        document.name,
                        doc.page_count,
                        RASTER_MAX_PAGES,
                    )
                return [
                    _render(doc[n], document.name)
                    for n in range(min(doc.page_count, RASTER_MAX_PAGES))
                ]
        except Exception as e:
            _logger.warning("Could not render %r: %s", document.name, e, exc_info=True)
            return []


register_reader(_PdfText())
register_reader(_XmlText())
register_reader(_Pages())
