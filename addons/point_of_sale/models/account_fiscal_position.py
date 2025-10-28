from odoo import models


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    def action_archive(self):
        configs = self.env['pos.config'].search([('default_fiscal_position_id', 'in', self.ids)])
        configs.default_fiscal_position_id = False
        return super().action_archive()
