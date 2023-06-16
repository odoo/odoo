# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SpreadsheetMixin(models.AbstractModel):
    _name = "spreadsheet.mixin"
    _description = "Spreadsheet mixin"
    _auto = False

    spreadsheet_binary_data = fields.Binary(
        required=True,
        string="Spreadsheet file",
        default=lambda self: self._empty_spreadsheet_data_base64(),
    )
    spreadsheet_data = fields.Text(compute='_compute_spreadsheet_data', inverse='_inverse_spreadsheet_data')
    thumbnail = fields.Binary()

    @api.depends("spreadsheet_binary_data")
    def _compute_spreadsheet_data(self):
        for spreadsheet in self.with_context(bin_size=False):
            if not spreadsheet.spreadsheet_binary_data:
                spreadsheet.spreadsheet_data = False
            else:
                spreadsheet.spreadsheet_data = base64.b64decode(spreadsheet.spreadsheet_binary_data).decode()

    def _inverse_spreadsheet_data(self):
        for spreadsheet in self:
            if not spreadsheet.spreadsheet_data:
                spreadsheet.spreadsheet_binary_data = False
            else:
                spreadsheet.spreadsheet_binary_data = base64.b64encode(spreadsheet.spreadsheet_data.encode())

    @api.onchange('spreadsheet_binary_data')
    def _onchange_data_(self):
        if self.spreadsheet_binary_data:
            try:
                data_str = base64.b64decode(self.spreadsheet_binary_data).decode('utf-8')
                json.loads(data_str)
            except:
                raise ValidationError(_('Invalid JSON Data'))

    def _empty_spreadsheet_data_base64(self):
        """Create an empty spreadsheet workbook.
        Encoded as base64
        """
        data = json.dumps(self._empty_spreadsheet_data())
        return base64.b64encode(data.encode())

    def _empty_spreadsheet_data(self):
        """Create an empty spreadsheet workbook.
        The sheet name should be the same for all users to allow consistent references
        in formulas. It is translated for the user creating the spreadsheet.
        """
        lang = self.env["res.lang"]._lang_get(self.env.user.lang)
        locale = lang._odoo_lang_to_spreadsheet_locale()
        return {
            "version": 1,
            "sheets": [
                {
                    "id": "sheet1",
                    "name": _("Sheet1"),
                }
            ],
            "settings": {
                "locale": locale,
            }
        }
