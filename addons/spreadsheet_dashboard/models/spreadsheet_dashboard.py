import json

from odoo import fields, models


class SpreadsheetDashboard(models.Model):
    _name = 'spreadsheet.dashboard'
    _description = 'Spreadsheet Dashboard'
    _inherit = "spreadsheet.mixin"
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    dashboard_group_id = fields.Many2one('spreadsheet.dashboard.group', required=True)
    sequence = fields.Integer()
    group_ids = fields.Many2many('res.groups', default=lambda self: self.env.ref('base.group_user'))


    def get_readonly_dashboard(self):
        self.ensure_one()
        snapshot = json.loads(self.spreadsheet_data)
        user_locale = self.env['res.lang']._get_user_spreadsheet_locale()
        snapshot.setdefault('settings', {})['locale'] = user_locale
        return {
            'snapshot': snapshot,
            'revisions': [],
        }
