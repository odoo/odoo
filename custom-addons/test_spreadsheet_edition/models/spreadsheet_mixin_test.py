from odoo import models


class SpreadsheetDummy(models.Model):
    _inherit = ['spreadsheet.test']

    def action_edit(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'fake_action',
            'params': {
                'spreadsheet_id': self.id,
            }
        }

    def _creation_msg(self):
        return "test spreadsheet created"
