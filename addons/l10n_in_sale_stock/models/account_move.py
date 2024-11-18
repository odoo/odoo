# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_in_get_warehouse_address(self):
        res = super()._l10n_in_get_warehouse_address()
        if self.invoice_line_ids.sale_line_ids:
            company_shipping_id = self.invoice_line_ids.sale_line_ids.order_id.warehouse_id.partner_id
            if len(company_shipping_id) == 1:
                return company_shipping_id
        return res
