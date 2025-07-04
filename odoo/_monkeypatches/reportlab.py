import logging

_logger = logging.getLogger(__name__)

try:
    from reportlab.graphics.barcode.ecc200datamatrix import ECC200DataMatrix
except ImportError:
    ECC200DataMatrix = None
    _logger.warning("reportlab.graphics.barcode.ecc200datamatrix not found. DataMatrix barcode generation might not work.")


def datamatrix_encode_ascii(value):
    """Encode ASCII data in a list of integer of ASCII value + 1,
    supporting Extended ASCII (ISO-8859-1) characters.
    """

    i = 0

    while i < len(value):
        c = value[i]
        char_ord = ord(c)

        if char_ord >= 128:
            yield 235
            yield char_ord - 127
            i += 1
        elif char_ord >= 48 and char_ord <= 57 and i + 1 < len(value) and value[i + 1].isdigit():
            yield 130 + int(value[i : i + 2])
            i += 2
        else:
            yield char_ord + 1
            i += 1


def patch_encode_c40(self, value):
    """
    Patched version of ECC200DataMatrix._encode_c40 to prevent trailing nul bytes.
    Also ensures compatibility with the updated datamatrix_encode_ascii for Extended ASCII.
    """

    if isinstance(value, str):
        value = value.replace('\x00', '')
    elif isinstance(value, bytes):
        value = value.replace(b'\x00', b'')

    encoded = []
    for c in value:
        c40_char = self._encode_c40_char(c)
        encoded.extend(c40_char)

    codewords = [230]

    length, remaining = divmod(len(encoded), 3)
    for i in range(length):
        total = encoded[i * 3] * 1600 + encoded[i * 3 + 1] * 40 + encoded[i * 3 + 2] + 1
        codewords.extend(divmod(total, 256))

    codewords.append(254)
    if remaining:
        index = 1 if (remaining == len(value) == 2 or len(value) == 0) else remaining
        if value[-index:]:
            codewords.extend(datamatrix_encode_ascii(value[-index:]))

    if len(codewords) > self.cw_data:
        raise Exception("Too much data to fit into a data matrix of this size")

    if len(codewords) < self.cw_data:
        codewords.append(129)  # End of data
        while len(codewords) < self.cw_data:
            r = ((149 * (len(codewords) + 1)) % 253) + 1
            codewords.append((129 + r) % 254)

    return codewords


def patch_reportlab():
    """
    Applies the patch to ECC200DataMatrix._encode_c40 if ECC200DataMatrix is available.
    """
    if ECC200DataMatrix is not None:
        ECC200DataMatrix._encode_c40 = patch_encode_c40
