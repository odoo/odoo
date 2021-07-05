# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class L10nInAccountInvoiceReport(models.Model):
    _inherit = "l10n_in.account.invoice.report"

    def _where(self):
        where_str = super()._where()
        where_str += """
            AND (
                parent_at.id is NULL
                OR
                parent_at.id in (
                  SELECT account_tax_id
                  FROM account_move_line_account_tax_rel aml_taxes
                  JOIN account_move_line aml2 on aml_taxes.account_move_line_id = aml2.id
                 WHERE aml2.move_id = aml.move_id
                   AND aml2.product_id = aml.product_id
                )
            )
        """
        return where_str
