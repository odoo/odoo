# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.onchange('product_id', 'date_order')
    def _onchange_product_id_date(self):
        default_analytic_account = self.env['account.analytic.default'].account_get(product_id=self.product_id.id, partner_id=self.order_id.partner_id.id, user_id=self.env.uid, date=self.date_order)
        if default_analytic_account:
            self.account_analytic_id = default_analytic_account.analytic_id.id
            self.analytic_tag_ids = [(6, 0, default_analytic_account.analytic_tag_ids.ids)]
