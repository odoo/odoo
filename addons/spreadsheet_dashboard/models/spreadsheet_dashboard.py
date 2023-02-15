import base64
import json

from odoo import api, fields, models, _

from odoo.addons.spreadsheet.utils import empty_spreadsheet_data_base64

class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _description = 'Spreadsheet Dashboard'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    dashboard_group_id = fields.Many2one('spreadsheet.dashboard.group', required=True)
    data = fields.Binary(required=True, default=lambda self: empty_spreadsheet_data_base64())
    spreadsheet_data = fields.Text(compute='_compute_spreadsheet_data')
    thumbnail = fields.Binary()
    sequence = fields.Integer()
    group_ids = fields.Many2many('res.groups', default=lambda self: self.env.ref('base.group_user'))

    @api.depends("data")
    def _compute_spreadsheet_data(self):
        for dashboard in self:
            dashboard.spreadsheet_data = base64.b64decode(dashboard.data).decode()
