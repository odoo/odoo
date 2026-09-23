from __future__ import annotations

import io
import logging

import zxingcpp
from PIL import Image

from odoo.libs.documents import BARCODES, CHEAP, BaseReader, register_reader

from odoo.addons.extract.tools import PAGED

_logger = logging.getLogger(__name__)


def read_page(image: bytes) -> list[str]:
    return [
        symbol.text for symbol in zxingcpp.read_barcodes(Image.open(io.BytesIO(image)))
    ]


class Barcodes(BaseReader):
    """What a document's pages carry printed as codes, decoded once each."""

    name = "zxing_barcodes"
    mimetypes = PAGED
    yields = (BARCODES,)
    cost = CHEAP

    def read(self, document):
        pages = document.images
        if not pages:
            return []
        found: list[str] = []
        for page in pages:
            # Tolerated per page, not per document: a decoder that chokes on one
            # rendering must not throw away the codes read off the others. The
            # reader the registry replaced did this, and only one page is ever
            # rendered today, so losing it would have been invisible until a
            # document with two was.
            try:
                found.extend(read_page(page))
            except Exception as e:
                _logger.warning(
                    "Barcode reader failed on a page of %r: %s",
                    document.name,
                    e,
                    exc_info=True,
                )
        return list(dict.fromkeys(found))


register_reader(Barcodes())
