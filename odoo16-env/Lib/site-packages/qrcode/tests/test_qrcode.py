import io
from unittest import mock

import pytest

import qrcode
import qrcode.util
from qrcode.exceptions import DataOverflowError
from qrcode.image.base import BaseImage
from qrcode.tests.consts import UNICODE_TEXT
from qrcode.util import MODE_8BIT_BYTE, MODE_ALPHA_NUM, MODE_NUMBER, QRData


def test_basic():
    qr = qrcode.QRCode(version=1)
    qr.add_data("a")
    qr.make(fit=False)


def test_large():
    qr = qrcode.QRCode(version=27)
    qr.add_data("a")
    qr.make(fit=False)


def test_invalid_version():
    with pytest.raises(ValueError):
        qrcode.QRCode(version=42)


def test_invalid_border():
    with pytest.raises(ValueError):
        qrcode.QRCode(border=-1)


def test_overflow():
    qr = qrcode.QRCode(version=1)
    qr.add_data("abcdefghijklmno")
    with pytest.raises(DataOverflowError):
        qr.make(fit=False)


def test_add_qrdata():
    qr = qrcode.QRCode(version=1)
    data = QRData("a")
    qr.add_data(data)
    qr.make(fit=False)


def test_fit():
    qr = qrcode.QRCode()
    qr.add_data("a")
    qr.make()
    assert qr.version == 1
    qr.add_data("bcdefghijklmno")
    qr.make()
    assert qr.version == 2


def test_mode_number():
    qr = qrcode.QRCode()
    qr.add_data("1234567890123456789012345678901234", optimize=0)
    qr.make()
    assert qr.version == 1
    assert qr.data_list[0].mode == MODE_NUMBER


def test_mode_alpha():
    qr = qrcode.QRCode()
    qr.add_data("ABCDEFGHIJ1234567890", optimize=0)
    qr.make()
    assert qr.version == 1
    assert qr.data_list[0].mode == MODE_ALPHA_NUM


def test_regression_mode_comma():
    qr = qrcode.QRCode()
    qr.add_data(",", optimize=0)
    qr.make()
    assert qr.data_list[0].mode == MODE_8BIT_BYTE


def test_mode_8bit():
    qr = qrcode.QRCode()
    qr.add_data("abcABC" + UNICODE_TEXT, optimize=0)
    qr.make()
    assert qr.version == 1
    assert qr.data_list[0].mode == MODE_8BIT_BYTE


def test_mode_8bit_newline():
    qr = qrcode.QRCode()
    qr.add_data("ABCDEFGHIJ1234567890\n", optimize=0)
    qr.make()
    assert qr.data_list[0].mode == MODE_8BIT_BYTE


def test_make_image_with_wrong_pattern():
    with pytest.raises(TypeError):
        qrcode.QRCode(mask_pattern="string pattern")

    with pytest.raises(ValueError):
        qrcode.QRCode(mask_pattern=-1)

    with pytest.raises(ValueError):
        qrcode.QRCode(mask_pattern=42)


def test_mask_pattern_setter():
    qr = qrcode.QRCode()

    with pytest.raises(TypeError):
        qr.mask_pattern = "string pattern"

    with pytest.raises(ValueError):
        qr.mask_pattern = -1

    with pytest.raises(ValueError):
        qr.mask_pattern = 8


def test_qrcode_bad_factory():
    with pytest.raises(TypeError):
        qrcode.QRCode(image_factory="not_BaseImage")  # type: ignore

    with pytest.raises(AssertionError):
        qrcode.QRCode(image_factory=dict)  # type: ignore


def test_qrcode_factory():
    class MockFactory(BaseImage):
        drawrect = mock.Mock()
        new_image = mock.Mock()

    qr = qrcode.QRCode(image_factory=MockFactory)
    qr.add_data(UNICODE_TEXT)
    qr.make_image()
    assert MockFactory.new_image.called
    assert MockFactory.drawrect.called


def test_optimize():
    qr = qrcode.QRCode()
    text = "A1abc12345def1HELLOa"
    qr.add_data(text, optimize=4)
    qr.make()
    assert [d.mode for d in qr.data_list] == [
        MODE_8BIT_BYTE,
        MODE_NUMBER,
        MODE_8BIT_BYTE,
        MODE_ALPHA_NUM,
        MODE_8BIT_BYTE,
    ]
    assert qr.version == 2


def test_optimize_short():
    qr = qrcode.QRCode()
    text = "A1abc1234567def1HELLOa"
    qr.add_data(text, optimize=7)
    qr.make()
    assert len(qr.data_list) == 3
    assert [d.mode for d in qr.data_list] == [
        MODE_8BIT_BYTE,
        MODE_NUMBER,
        MODE_8BIT_BYTE,
    ]
    assert qr.version == 2


def test_optimize_longer_than_data():
    qr = qrcode.QRCode()
    text = "ABCDEFGHIJK"
    qr.add_data(text, optimize=12)
    assert len(qr.data_list) == 1
    assert qr.data_list[0].mode == MODE_ALPHA_NUM


def test_optimize_size():
    text = "A1abc12345123451234512345def1HELLOHELLOHELLOHELLOa" * 5

    qr = qrcode.QRCode()
    qr.add_data(text)
    qr.make()
    assert qr.version == 10

    qr = qrcode.QRCode()
    qr.add_data(text, optimize=0)
    qr.make()
    assert qr.version == 11


def test_qrdata_repr():
    data = b"hello"
    data_obj = qrcode.util.QRData(data)
    assert repr(data_obj) == repr(data)


def test_print_ascii_stdout():
    qr = qrcode.QRCode()
    with mock.patch("sys.stdout") as fake_stdout:
        fake_stdout.isatty.return_value = None
        with pytest.raises(OSError):
            qr.print_ascii(tty=True)
        assert fake_stdout.isatty.called


def test_print_ascii():
    qr = qrcode.QRCode(border=0)
    f = io.StringIO()
    qr.print_ascii(out=f)
    printed = f.getvalue()
    f.close()
    expected = "\u2588\u2580\u2580\u2580\u2580\u2580\u2588"
    assert printed[: len(expected)] == expected

    f = io.StringIO()
    f.isatty = lambda: True
    qr.print_ascii(out=f, tty=True)
    printed = f.getvalue()
    f.close()
    expected = "\x1b[48;5;232m\x1b[38;5;255m" + "\xa0\u2584\u2584\u2584\u2584\u2584\xa0"
    assert printed[: len(expected)] == expected


def test_print_tty_stdout():
    qr = qrcode.QRCode()
    with mock.patch("sys.stdout") as fake_stdout:
        fake_stdout.isatty.return_value = None
        pytest.raises(OSError, qr.print_tty)
        assert fake_stdout.isatty.called


def test_print_tty():
    qr = qrcode.QRCode()
    f = io.StringIO()
    f.isatty = lambda: True
    qr.print_tty(out=f)
    printed = f.getvalue()
    f.close()
    BOLD_WHITE_BG = "\x1b[1;47m"
    BLACK_BG = "\x1b[40m"
    WHITE_BLOCK = BOLD_WHITE_BG + "  " + BLACK_BG
    EOL = "\x1b[0m\n"
    expected = BOLD_WHITE_BG + "  " * 23 + EOL + WHITE_BLOCK + "  " * 7 + WHITE_BLOCK
    assert printed[: len(expected)] == expected


def test_get_matrix():
    qr = qrcode.QRCode(border=0)
    qr.add_data("1")
    assert qr.get_matrix() == qr.modules


def test_get_matrix_border():
    qr = qrcode.QRCode(border=1)
    qr.add_data("1")
    matrix = [row[1:-1] for row in qr.get_matrix()[1:-1]]
    assert matrix == qr.modules


def test_negative_size_at_construction():
    with pytest.raises(ValueError):
        qrcode.QRCode(box_size=-1)


def test_negative_size_at_usage():
    qr = qrcode.QRCode()
    qr.box_size = -1
    with pytest.raises(ValueError):
        qr.make_image()
