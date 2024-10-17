from unittest import mock

import pytest

from qrcode import run_example

pytest.importorskip("PIL", reason="Requires PIL")


@mock.patch("PIL.Image.Image.show")
def test_example(mock_show):
    run_example()
    mock_show.assert_called_with()
