import builtins
import datetime
import re
from unittest import mock

from qrcode.release import update_manpage

OPEN = f"{builtins.__name__}.open"
DATA = 'test\n.TH "date" "version" "description"\nthis'


@mock.patch(OPEN, new_callable=mock.mock_open, read_data=".TH invalid")
def test_invalid_data(mock_file):
    update_manpage({"name": "qrcode", "new_version": "1.23"})
    mock_file.assert_called()
    mock_file().write.assert_not_called()


@mock.patch(OPEN, new_callable=mock.mock_open, read_data=DATA)
def test_not_qrcode(mock_file):
    update_manpage({"name": "not-qrcode"})
    mock_file.assert_not_called()


@mock.patch(OPEN, new_callable=mock.mock_open, read_data=DATA)
def test_no_change(mock_file):
    update_manpage({"name": "qrcode", "new_version": "version"})
    mock_file.assert_called()
    mock_file().write.assert_not_called()


@mock.patch(OPEN, new_callable=mock.mock_open, read_data=DATA)
def test_change(mock_file):
    update_manpage({"name": "qrcode", "new_version": "3.11"})
    expected = re.split(r"([^\n]*(?:\n|$))", DATA)[1::2]
    expected[1] = (
        expected[1]
        .replace("version", "3.11")
        .replace("date", datetime.datetime.now().strftime("%-d %b %Y"))
    )
    mock_file().write.assert_has_calls(
        [mock.call(line) for line in expected if line != ""], any_order=True
    )
