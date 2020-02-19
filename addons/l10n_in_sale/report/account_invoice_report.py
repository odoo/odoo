# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class L10nInAccountInvoiceReport(models.Model):
    _inherit = "l10n_in.account.invoice.report"

    def _where(self):
        where_str = super(L10nInAccountInvoiceReport, self)._where()
        where_str += """ AND (aml.product_id IS NULL or aml.product_id != COALESCE(
            (SELECT value from ir_config_parameter where key = 'sale.default_deposit_product_id'), '0')::int)
            """
        return where_str
