import json
import base64

from odoo import _

def empty_spreadsheet_data_base64():
    """Create an empty spreadsheet workbook.
    Encoded as base64
    """
    data = json.dumps(empty_spreadsheet_data())
    return base64.b64encode(data.encode())

def empty_spreadsheet_data():
    """Create an empty spreadsheet workbook.
    The sheet name should be the same for all users to allow consistent references
    in formulas. It is translated for the user creating the spreadsheet.
    """
    return {
        "version": 1,
        "sheets": [
            {
                "id": "sheet1",
                "name": _("Sheet1"),
            }
        ]
    }
