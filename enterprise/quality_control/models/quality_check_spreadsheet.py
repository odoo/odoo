
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class QualityCheckSpreadsheet(models.Model):
    _name = 'quality.check.spreadsheet'
    _description = "Quality check spreadsheet"
    _inherit = 'spreadsheet.mixin'

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company
    )
    check_cell = fields.Char(
        string="Success cell",
        help="The check is successful if the success cell value is TRUE. If there are"
        " several sheets, specify which one you want to use (e.g. Sheet2!C4). If not "
        "specified, the first sheet is selected by default.",
    )

    def get_formview_action(self, access_uid=None):
        return self.action_open_spreadsheet()

    def action_open_spreadsheet(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'action_spreadsheet_quality',
            'params': {
                'spreadsheet_id': self.id,
            },
        }

    def join_spreadsheet_session(self, access_token=None):
        data = super().join_spreadsheet_session(access_token)
        check = self.env['quality.check'].search([('spreadsheet_id', '=', self.id)], limit=1)
        data['quality_check_display_name'] = check.display_name
        data['quality_check_cell'] = self.check_cell
        return data

    @api.autovacuum
    def _gc_spreadsheet_history(self):
        self.env['spreadsheet.revision']._gc_revisions(
            [('res_model', '=', self._name)],
            inactivity_days=1,
        )
