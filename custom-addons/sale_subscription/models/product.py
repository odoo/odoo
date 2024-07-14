# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class product_template(models.Model):
    _inherit = "product.template"

    recurring_invoice = fields.Boolean(
        'Subscription Product',
        help='If set, confirming a sale order with this product will create a subscription')

    product_subscription_pricing_ids = fields.One2many(
        'sale.subscription.pricing', 'product_template_id', string="Custom Subscription Pricings",
        auto_join=True, copy=False, groups='sales_team.group_sale_salesman'
    )

    @api.model
    def _get_incompatible_types(self):
        return ['recurring_invoice'] + super()._get_incompatible_types()

    @api.onchange('recurring_invoice')
    def _onchange_recurring_invoice(self):
        """
        Raise a warning if the user has checked 'Subscription Product'
        while the product has already been sold.
        In this case, the 'Subscription Product' field is automatically
        unchecked.
        """
        confirmed_lines = self.env['sale.order.line'].search([
            ('product_template_id', 'in', self.ids),
            ('state', '=', 'sale')])
        if confirmed_lines:
            self.recurring_invoice = not self.recurring_invoice
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "You can not change the recurring property of this product because it has been sold already.")
            }}

    def copy(self, default=None):
        copied_tmpl = super().copy(default)
        for pricing in self.product_subscription_pricing_ids:
            copied_variant_ids = []
            for product in pricing.product_variant_ids:
                pav_ids = product.product_template_variant_value_ids.product_attribute_value_id.ids
                copied_variant_ids.extend(
                    copied_tmpl.product_variant_ids.filtered(
                        lambda p: p
                            .product_template_variant_value_ids
                            .product_attribute_value_id
                            .ids == pav_ids
                    ).ids
                )
            pricing.copy({
                'product_template_id': copied_tmpl.id,
                'product_variant_ids': copied_variant_ids,
            })
        return copied_tmpl
