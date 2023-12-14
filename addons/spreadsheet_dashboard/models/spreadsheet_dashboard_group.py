from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SpreadsheetDashboardGroup(models.Model):
    _name = 'spreadsheet.dashboard.group'
    _description = 'Group of dashboards'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    dashboard_ids = fields.One2many('spreadsheet.dashboard', 'dashboard_group_id')
    published_dashboard_ids = fields.One2many('spreadsheet.dashboard', 'dashboard_group_id', domain=[('is_published', '=', True)])
    sequence = fields.Integer()

    @api.ondelete(at_uninstall=False)
    def _unlink_except_spreadsheet_data(self):
        external_ids = self.get_external_id()
        for group in self:
            external_id = external_ids[group.id]
            if external_id and not external_id.startswith('__export__'):
                raise UserError(_("You cannot delete %s as it is used in another module.", group.name))
