# Part of Odoo. See LICENSE file for full copyright and licensing details.
import functools
import re
from threading import RLock

__all__ = ['check_barcode_encoding', 'createBarcodeDrawing', 'get_barcode_font']
_barcode_init_lock = RLock()


# A lock occurs when the user wants to print a report having multiple barcode while the server is
# started in threaded-mode. The reason is that reportlab has to build a cache of the T1 fonts
# before rendering a barcode (done in a C extension) and this part is not thread safe.
# This cached functions allows to lazily initialize the T1 fonts cache need for rendering of
# barcodes in a thread-safe way.
@functools.lru_cache(1)
def _init_barcode():
    with _barcode_init_lock:
        try:
            from reportlab.graphics import barcode  # noqa: PLC0415
            from reportlab.pdfbase.pdfmetrics import TypeFace, getFont  # noqa: PLC0415
            font_name = 'Courier'
            available = TypeFace(font_name).findT1File()
            if not available:
                substitution_font = 'NimbusMonoPS-Regular'
                fnt = getFont(substitution_font)
                if fnt:
                    font_name = substitution_font
                    fnt.ascent = 629
                    fnt.descent = -157
            barcode.createBarcodeDrawing('Code128', value='foo', format='png', width=100, height=100, humanReadable=1, fontName=font_name).asString('png')
        except ImportError:
            raise
        except Exception:  # noqa: BLE001
            font_name = 'Courier'
        return barcode, font_name


def createBarcodeDrawing(codeName: str, **options):
    barcode, _font = _init_barcode()
    return barcode.createBarcodeDrawing(codeName, **options)


def get_barcode_font():
    """Get the barcode font for rendering."""
    _barcode, font = _init_barcode()
    return font


def get_barcode_check_digit(numeric_barcode: str) -> int:
    """ Computes and returns the barcode check digit. The used algorithm
    follows the GTIN specifications and can be used by all compatible
    barcode nomenclature, like as EAN-8, EAN-12 (UPC-A) or EAN-13.
    https://www.gs1.org/sites/default/files/docs/barcodes/GS1_General_Specifications.pdf
    https://www.gs1.org/services/how-calculate-check-digit-manually
    :param numeric_barcode: the barcode to verify/recompute the check digit
    :return: the number corresponding to the right check digit
    """
    # Multiply value of each position by
    # N1  N2  N3  N4  N5  N6  N7  N8  N9  N10 N11 N12 N13 N14 N15 N16 N17 N18
    # x3  X1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  x1  x3  CHECKSUM
    oddsum = evensum = 0
    code = numeric_barcode[-2::-1]  # Remove the check digit and reverse the barcode.
    # The CHECKSUM digit is removed because it will be recomputed and it must not interfer with
    # the computation. Also, the barcode is inverted, so the barcode length doesn't matter.
    # Otherwise, the digits' group (even or odd) could be different according to the barcode length.
    for i, digit in enumerate(code):
        if i % 2 == 0:
            evensum += int(digit)
        else:
            oddsum += int(digit)
    total = evensum * 3 + oddsum
    return (10 - total % 10) % 10


def check_barcode_encoding(barcode: str, encoding: str) -> bool:
    """ Checks if the given barcode is correctly encoded.
    :return: True if the barcode string is encoded with the provided encoding.
    """
    encoding = encoding.lower()
    if encoding == "any":
        return True
    barcode_sizes = {
        'ean8': 8,
        'ean13': 13,
        'gtin14': 14,
        'upca': 12,
        'sscc': 18,
    }
    barcode_size = barcode_sizes[encoding]
    return (encoding != 'ean13' or barcode[0] != '0') \
           and len(barcode) == barcode_size \
           and re.match(r"^\d+$", barcode) \
           and get_barcode_check_digit(barcode) == int(barcode[-1])
