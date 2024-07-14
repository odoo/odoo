# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Technical fields to hold prices for TaxCloud
    price_taxcloud = fields.Float('Taxcloud Price', default=0)

    def _check_taxcloud_promo(self, vals):
        """Ensure that users cannot modify sale order lines of a Taxcloud order
           with promotions if there is already a valid invoice"""

        blocked_fields = (
            'product_id',
            'price_unit',
            'price_subtotal',
            'price_tax',
            'price_total',
            'tax_id',
            'discount',
            'product_id',
            'product_uom_qty',
            'product_qty'
        )
        for line in self:
            if (
                line.order_id.is_taxcloud
                and not line.display_type
                and any(field in vals for field in blocked_fields)
                and any(line.order_id.order_line.mapped(lambda sol: sol.invoice_status not in ('no', 'to invoice')))
                and any(line.order_id.order_line.mapped('is_reward_line'))
            ):
                raise UserError(
                    _(
                    'Orders with coupons or promotions programs that use TaxCloud for '
                    'automatic tax computation cannot be modified after having been invoiced.\n'
                    'To modify this order, you must first cancel or refund all existing invoices.'
                    )
                )

    def write(self, vals):
        self._check_taxcloud_promo(vals)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        for line, vals in zip(lines, vals_list):
            line._check_taxcloud_promo(vals)
        return lines

    def _get_taxcloud_price(self):
        self.ensure_one()
        return self.price_taxcloud

    def _prepare_invoice_line(self, **optional_values):
        res = super()._prepare_invoice_line(**optional_values)
        res.update(reward_id=self.reward_id.id)
        return res
