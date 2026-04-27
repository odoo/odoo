# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class IrModel(models.Model):
    _inherit = 'ir.model'

    @api.ondelete(at_uninstall=False)
    def _delete(self):
        self.env['worksheet.template']\
            .with_context(active_test=False)\
            .search([('model_id', 'in', self.ids)])\
            .unlink()
