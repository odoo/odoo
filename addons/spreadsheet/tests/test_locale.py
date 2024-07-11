from odoo.tests.common import TransactionCase
from odoo.addons.spreadsheet.utils import (
    strftime_format_to_spreadsheet_time_format,
    strftime_format_to_spreadsheet_date_format,
)


class TestLocale(TransactionCase):
    def test_time_format_conversion(self):
        # Simple format
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%H:%M:%S"), "hh:mm:ss")

        # AM/PM
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%I:%M:%S"), "hh:mm:ss a")
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%H:%M:%S %p"), "hh:mm:ss a")

        # Separator
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%H %M %S"), "hh mm ss")
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%H %M:%S"), "hh mm ss")
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%H-%M-%S"), "hh:mm:ss")

        # Escaped characters are ignored
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%H시 %M분 %S초"), "hh mm ss")

        # Unsupported format code are ignored
        self.assertEqual(strftime_format_to_spreadsheet_time_format("%H:%M:%S %f %z"), "hh:mm:ss")

    def test_date_format_conversion(self):
        # Simple format
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%m/%d/%Y"), "mm/dd/yyyy")

        # Various formats code
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%b/%a/%y"), "mmm/ddd/yy")
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%B/%A/%Y"), "mmmm/dddd/yyyy")

        # Separator
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%m %d %Y"), "mm dd yyyy")
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%m-%d-%Y"), "mm-dd-yyyy")
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%m/%d/%Y"), "mm/dd/yyyy")
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%m-%d/%Y"), "mm-dd-yyyy")
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%m.%d.%Y"), "mm/dd/yyyy")

        # Escaped characters are ignored
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%a, %Y.eko %bren %da"), "ddd yyyy mmm dd")
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%Y년 %m월 %d일"), "yyyy mm dd")

        # Unsupported format code are ignored
        self.assertEqual(strftime_format_to_spreadsheet_date_format("%w %x %Z %j %m %d %Y"), "mm dd yyyy")
