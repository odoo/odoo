# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import format_amount

class SaleSubscriptionPricing(models.Model):
    _name = 'sale.subscription.pricing'
    _description = 'Pricing rule of subscription products'
    _order = 'product_template_id, price, pricelist_id, plan_id'

    active = fields.Boolean('Active', default=True)
    name = fields.Char(related="plan_id.billing_period_display")

    product_template_id = fields.Many2one('product.template', string="Products", ondelete='cascade',
                                          help="Select products on which this pricing will be applied.")
    product_variant_ids = fields.Many2many('product.product', string="Product Variants",
                                           help="Select Variants of the Product for which this rule applies. Leave empty if this rule applies for any variant of this template.")

    plan_id = fields.Many2one('sale.subscription.plan', string='Recurring Plan', required=True)
    pricelist_id = fields.Many2one('product.pricelist', ondelete='cascade')
    company_id = fields.Many2one('res.company', related='plan_id.company_id')

    price = fields.Monetary(string="Recurring Price", required=True, default=1.0)
    currency_id = fields.Many2one('res.currency', 'Currency', compute='_compute_currency_id', store=True)

    @api.constrains('plan_id', 'pricelist_id', 'product_template_id', 'product_variant_ids')
    def _unique_pricing_constraint(self):
        pricings_per_group = self._read_group(
            domain=[
                ('product_template_id', 'in', self.product_template_id.ids),
                ('plan_id', 'in', self.plan_id.ids),
                ('pricelist_id', 'in', self.pricelist_id.ids + ([False] if not self.filtered('pricelist_id') else [])),
            ],
            groupby=['product_template_id', 'plan_id', 'pricelist_id'],
            aggregates=['id:recordset'],
            having=[('__count', '>', 1)],
        )
        for product_template, __, __, pricings in pricings_per_group:
            already_covered = set()
            for pricing in pricings:
                pricing_covered = pricing.product_variant_ids.ids
                if not pricing_covered:
                    pricing_covered = product_template.product_variant_ids.ids
                if not already_covered.isdisjoint(pricing_covered):
                    raise UserError(_("There are multiple pricings for an unique product, plan and pricelist."))
                already_covered.update(pricing_covered)

    @api.constrains('pricelist_id')
    def _unique_company_contraint(self):
        if self.company_id and self.pricelist_id.company_id and self.company_id != self.pricelist_id.company_id:
            raise UserError(_("The company of the plan is different from the company of the pricelist"))

    def _compute_description(self):
        for pricing in self:
            pricing.description = f"{format_amount(self.env, amount=pricing.price, currency=pricing.currency_id)} / {self.name}"

    @api.depends('pricelist_id', 'pricelist_id.currency_id')
    def _compute_currency_id(self):
        for pricing in self:
            if pricing.pricelist_id:
                pricing.currency_id = pricing.pricelist_id.currency_id
            else:
                pricing.currency_id = self.env.company.currency_id

    def _applies_to(self, product):
        """ Check whether current pricing applies to given product.
        :param product.product product:
        :return: true if current pricing is applicable for given product, else otherwise.
        """
        self.ensure_one()
        return (self.product_template_id == product.product_tmpl_id
                and (
                        not self.product_variant_ids
                        or product in self.product_variant_ids))

    @api.model
    def _get_first_suitable_recurring_pricing(self, product, plan=None, pricelist=None):
        """ Get a suitable pricing for given product and pricelist.
        Note: model method
        """
        if self.env.is_superuser():   # This is for access to the product pricing
            product = product.sudo()
        is_product_template = product._name == "product.template"
        available_pricings = product.product_subscription_pricing_ids
        first_pricing = self.env['sale.subscription.pricing']
        for pricing in available_pricings:
            if plan and pricing.plan_id != plan:
                continue
            if pricing.pricelist_id == pricelist and (is_product_template or pricing._applies_to(product)):
                return pricing
            if not first_pricing and not pricing.pricelist_id and (is_product_template or pricing._applies_to(product)):
                # If price list and current pricing is not part of it,
                # We store the first one to return if not pricing matching the price list is found.
                first_pricing = pricing
        return first_pricing
