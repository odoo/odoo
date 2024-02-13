import json

from odoo import _, api, fields, models


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

    @api.returns('self')
    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [dict(vals, name=_("%s (copy)", dashboard.name)) for dashboard, vals in zip(self, vals_list)]
