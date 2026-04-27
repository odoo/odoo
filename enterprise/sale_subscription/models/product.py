# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import format_amount


class product_template(models.Model):
    _inherit = "product.template"

    recurring_invoice = fields.Boolean(
        'Subscription Product',
        help='If set, confirming a sale order with this product will create a subscription')

    product_subscription_pricing_ids = fields.One2many(
        'sale.subscription.pricing', 'product_template_id', string="Custom Subscription Pricings",
        auto_join=True, copy=False, groups='sales_team.group_sale_salesman'
    )
    display_subscription_pricing = fields.Char('Display Price', compute='_compute_display_subscription_pricing')

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
            self.recurring_invoice = self._origin.recurring_invoice
            return {'warning': {
                'title': _("Warning"),
                'message': _(
                    "You can not change the recurring property of this product because it has been sold already.")
            }}

    @api.depends('product_subscription_pricing_ids')
    def _compute_display_subscription_pricing(self):
        for record in self:
            pricing_ids = record.sudo().product_subscription_pricing_ids
            if pricing_ids:
                display_pricing = pricing_ids[0]
                formatted_price = format_amount(self.env, display_pricing.price, display_pricing.currency_id)
                record.display_subscription_pricing = _(
                    '%(price)s %(billing_period_display_sentence)s',
                    price=formatted_price,
                    billing_period_display_sentence=display_pricing.plan_id.billing_period_display_sentence
                )
            else:
                record.display_subscription_pricing = None

    @api.constrains('type', 'combo_ids', 'recurring_invoice')
    def _check_subscription_combo_ids(self):
        for template in self:
            if (
                template.type == 'combo'
                and template.recurring_invoice
                and any(
                    not product.recurring_invoice
                    for product in template.combo_ids.combo_item_ids.product_id
                )
            ):
                raise ValidationError(
                    _("A subscription combo product can only contain subscription products.")
                )

    def copy(self, default=None):
        copied_tmpls = self.env['product.template']
        for record in self:
            copied_tmpl = super(product_template, record).copy(default)
            if not record.sudo().product_subscription_pricing_ids:
                copied_tmpls += copied_tmpl
                continue
            if not self.env.user.has_group('sales_team.group_sale_salesman'):
                raise UserError(_(
                    "You cannot copy a product with custom subscription pricing without sales application access.")
                )
            copied_tmpls += copied_tmpl
            for pricing in record.product_subscription_pricing_ids:
                copied_variant_ids = []
                for product in pricing.product_variant_ids:
                    pav_ids = product\
                        .product_template_variant_value_ids\
                        .product_attribute_value_id\
                        .ids
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
        return copied_tmpls

    @api.model
    def _get_configurator_price(
        self, product_or_template, quantity, date, currency, pricelist, plan_id=None, **kwargs
    ):
        """ Override of `sale` to compute the subscription price.

        :param product.product|product.template product_or_template: The product for which to get
            the price.
        :param int quantity: The quantity of the product.
        :param datetime date: The date to use to compute the price.
        :param res.currency currency: The currency to use to compute the price.
        :param product.pricelist pricelist: The pricelist to use to compute the price.
        :param int|None plan_id: The subscription plan of the product, as a `sale.subscription.plan`
            id.
        :param dict kwargs: Locally unused data passed to `super`.
        :rtype: float
        :return: The specified product's price.
        """
        price, pricelist_rule_id = super()._get_configurator_price(
            product_or_template, quantity, date, currency, pricelist, plan_id=plan_id, **kwargs
        )

        if (
            product_or_template.recurring_invoice
            and (pricing := self._get_pricing(product_or_template, pricelist, plan_id=plan_id))
        ):
            return pricing.currency_id._convert(
                from_amount=pricing.price,
                to_currency=currency,
                company=self.env.company,
                date=date,
            ), False
        return price, pricelist_rule_id

    @api.model
    def _get_additional_configurator_data(
        self, product_or_template, date, currency, pricelist, plan_id=None, **kwargs
    ):
        """ Override of `sale` to append subscription data.

        :param product.product|product.template product_or_template: The product for which to get
            additional data.
        :param datetime date: The date to use to compute prices.
        :param res.currency currency: The currency to use to compute prices.
        :param product.pricelist pricelist: The pricelist to use to compute prices.
        :param int|None plan_id: The subscription plan of the product, as a `sale.subscription.plan`
            id.
        :param dict kwargs: Locally unused data passed to `super`.
        :rtype: dict
        :return: A dict containing additional data about the specified product.
        """
        data = super()._get_additional_configurator_data(
            product_or_template, date, currency, pricelist, plan_id=plan_id, **kwargs
        )

        if (
            product_or_template.recurring_invoice
            and (pricing := self._get_pricing(product_or_template, pricelist, plan_id=plan_id))
        ):
            data['price_info'] = pricing.plan_id.billing_period_display_sentence
        return data

    @api.model
    def _get_pricing(self, product_or_template, pricelist, plan_id=None):
        """ Return the specified product's pricing.

        :param product.product|product.template product_or_template: The product for which to get
            the pricing.
        :param product.pricelist pricelist: The pricelist to use to compute the pricing.
        :param int|None plan_id: The subscription plan of the product, as a `sale.subscription.plan`
            id.
        :rtype: sale.subscription.pricing
        :return: The specified product's pricing.
        """
        subscription_plan = self.env['sale.subscription.plan'].browse(plan_id)
        return self.env['sale.subscription.pricing'].sudo()._get_first_suitable_recurring_pricing(
            product_or_template, plan=subscription_plan, pricelist=pricelist
        )
