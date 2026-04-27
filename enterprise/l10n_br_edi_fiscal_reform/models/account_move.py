# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_br_get_line_uom(self, line_id):
        # Override.
        return self.env['account.move.line'].browse(line_id).product_uom_id

    def _l10n_br_build_avatax_line(self, product, qty, unit_price, total, discount, line_id):
        res = super()._l10n_br_build_avatax_line(product, qty, unit_price, total, discount, line_id)
        if not self.company_id.l10n_br_is_icbs:
            return res

        aml = self.env['account.move.line'].browse(line_id)
        if aml.l10n_br_cbs_ibs_deduction:
            deductions = res.setdefault('taxDeductions', {})
            deductions['cbsIbs'] = aml.l10n_br_cbs_ibs_deduction

        return res
