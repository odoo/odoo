from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _eligible_for_cogs(self):
        self.ensure_one()
        return super()._eligible_for_cogs() and not any(sol.is_rental for sol in self.sale_line_ids)
