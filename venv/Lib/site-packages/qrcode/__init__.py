from qrcode.main import QRCode
from qrcode.main import make  # noqa
from qrcode.constants import (  # noqa
    ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H)

from qrcode import image  # noqa


def run_example(data="http://www.lincolnloop.com", *args, **kwargs):
    """
    Build an example QR Code and display it.

    There's an even easier way than the code here though: just use the ``make``
    shortcut.
    """
    qr = QRCode(*args, **kwargs)
    qr.add_data(data)

    im = qr.make_image()
    im.show()


if __name__ == '__main__':  # pragma: no cover
    import sys
    run_example(*sys.argv[1:])
