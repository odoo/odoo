import pytest

from qrcode import util


def test_check_wrong_version():
    with pytest.raises(ValueError):
        util.check_version(0)

    with pytest.raises(ValueError):
        util.check_version(41)
