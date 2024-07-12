# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    def _prepare_invoice_values(self, order, so_line, accounts):
        res = super()._prepare_invoice_values(order, so_line, accounts)
        if order.country_code == 'IN':
            res['l10n_in_gst_treatment'] = order.l10n_in_gst_treatment
        if order.l10n_in_reseller_partner_id:
            res['l10n_in_reseller_partner_id'] = order.l10n_in_reseller_partner_id
        return res
