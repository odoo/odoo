import base64
import json

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from odoo.addons.spreadsheet.utils import empty_spreadsheet_data_base64

class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _description = 'Spreadsheet Dashboard'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    dashboard_group_id = fields.Many2one('spreadsheet.dashboard.group', required=True)
    data = fields.Binary(required=True, default=lambda self: empty_spreadsheet_data_base64())
    raw = fields.Binary(compute='_compute_raw')
    thumbnail = fields.Binary()
    sequence = fields.Integer()
    group_ids = fields.Many2many('res.groups', default=lambda self: self.env.ref('base.group_user'))

    @api.depends('data')
    def _compute_raw(self):
        for dashboard in self:
            dashboard.raw = base64.decodebytes(dashboard.data)

    @api.onchange('data')
    def _onchange_data_(self):
        if self.data:
            try:
                data_str = base64.b64decode(self.data).decode('utf-8')
                json.loads(data_str)
            except:
                raise ValidationError(_('Invalid JSON Data'))
