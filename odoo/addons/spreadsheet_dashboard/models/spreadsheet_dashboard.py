import json

from odoo import _, fields, models


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
        default_currency = self.env['res.currency'].get_company_currency_for_spreadsheet()
        return {
            'snapshot': snapshot,
            'revisions': [],
            'default_currency': default_currency,
        }

    def copy(self, default=None):
        self.ensure_one()
        if default is None:
            default = {}
        if 'name' not in default:
            default['name'] = _("%s (copy)") % self.name
        return super().copy(default=default)
