# -*- coding: utf-8 -*-

from odoo import models


class AccountTax(models.Model):
    _inherit = "account.tax"

    def _hook_compute_is_used(self, taxes_to_compute):
        # OVERRIDE in order to fetch taxes used in purchase

        used_taxes = super()._hook_compute_is_used(taxes_to_compute)
        taxes_to_compute -= used_taxes

        if taxes_to_compute:
            self.env['purchase.order.line'].flush_model(['tax_ids'])
            self.env.cr.execute("""
                SELECT id
                FROM account_tax
                WHERE EXISTS(
                    SELECT 1
                    FROM account_tax_purchase_order_line_rel AS pur
                    WHERE account_tax_id IN %s
                    AND account_tax.id = pur.account_tax_id
                )
            """, [tuple(taxes_to_compute)])

            used_taxes.update([tax[0] for tax in self.env.cr.fetchall()])

        return used_taxes
