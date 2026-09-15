import logging
import re
from threading import RLock
from typing import Any

from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

__all__ = [
    "createBarcodeDrawing",
    "get_barcode_check_digit",
    "get_barcode_font",
    "is_barcode_encoding_valid",
]
_barcode_init_lock: RLock = RLock()


_barcode_init: tuple[Any, str] | None = None


def _init_barcode() -> tuple[Any, str]:
    global _barcode_init  # noqa: PLW0603  one-shot lazy init of the reportlab barcode tables
    with _barcode_init_lock:
        if _barcode_init is not None:
            return _barcode_init
        try:
            from reportlab.graphics import barcode
            from reportlab.pdfbase.pdfmetrics import TypeFace, getFont

            font_name = "Courier"
            available = TypeFace(font_name).findT1File()
            if not available:
                substitution_font = "NimbusMonoPS-Regular"
                fnt = getFont(substitution_font)
                if fnt:
                    font_name = substitution_font
                    fnt.ascent = 629
                    fnt.descent = -157
            barcode.createBarcodeDrawing(
                "Code128",
                value="foo",
                format="png",
                width=100,
                height=100,
                humanReadable=1,
                fontName=font_name,
            ).asString("png")
        except ImportError:
            _debug.lifecycle("barcode.init", available=False)
            raise
        except Exception:
            _logger.warning(
                "Barcode font %r could not be validated; falling back to Courier.",
                font_name,
                exc_info=True,
            )
            font_name = "Courier"
        _barcode_init = (barcode, font_name)
        _debug.lifecycle(
            "barcode.init",
            available=True,
            font=font_name,
            substituted=font_name != "Courier",
        )
        return _barcode_init


def createBarcodeDrawing(codeName: str, **options: Any) -> Any:
    barcode, _font = _init_barcode()
    return barcode.createBarcodeDrawing(codeName, **options)


def get_barcode_font() -> str:
    _barcode, font = _init_barcode()
    return font


_ASCII_DIGITS_RE = re.compile(r"\A[0-9]+\Z")


def get_barcode_check_digit(numeric_barcode: str) -> int:
    if not _ASCII_DIGITS_RE.match(numeric_barcode or ""):
        msg = f"barcode must be a non-empty string of ASCII digits, got {numeric_barcode!r}"
        raise ValueError(msg)

    oddsum = evensum = 0
    code = numeric_barcode[-2::-1]
    for i, digit in enumerate(code):
        if i % 2 == 0:
            evensum += int(digit)
        else:
            oddsum += int(digit)
    total = evensum * 3 + oddsum
    return (10 - total % 10) % 10


_BARCODE_SIZES = {
    "ean8": 8,
    "ean13": 13,
    "gtin14": 14,
    "upca": 12,
    "sscc": 18,
}


def is_barcode_encoding_valid(barcode: str, encoding: str) -> bool:
    encoding = encoding.lower()
    if encoding == "any":
        return True
    barcode_size = _BARCODE_SIZES.get(encoding)
    if barcode_size is None:
        _debug.logic("barcode.encoding_unknown", encoding=encoding)
        return False
    valid = bool(
        len(barcode) == barcode_size
        and _ASCII_DIGITS_RE.match(barcode)
        and (encoding != "ean13" or barcode[0] != "0")
        and get_barcode_check_digit(barcode) == int(barcode[-1])
    )
    if not valid:
        _debug.logic(
            "barcode.invalid",
            encoding=encoding,
            length=len(barcode),
            expected=barcode_size,
            digits=bool(_ASCII_DIGITS_RE.match(barcode)),
        )
    return valid
