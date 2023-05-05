# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import json
from odoo import api, fields, models, _
from odoo.addons.spreadsheet.utils import empty_spreadsheet_data_base64
from odoo.exceptions import ValidationError

class SpreadsheetMixin(models.AbstractModel):
    _name = "spreadsheet.mixin"
    _description = "Spreadsheet mixin"
    _auto = False

    spreadsheet_binary_data = fields.Binary(required=True, string="Spreadsheet file", default=empty_spreadsheet_data_base64())
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
