# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import format_amount

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.constrains('optional_product_ids')
    def _constraints_optional_product_ids(self):
        for template in self:
            if not template.recurring_invoice:
                continue
            plan_ids = set(template.product_subscription_pricing_ids.plan_id.ids)
            for optional_template in template.optional_product_ids:
                if not optional_template.recurring_invoice:
                    continue
                optional_plan_ids = optional_template.product_subscription_pricing_ids.plan_id.ids
                if not plan_ids.intersection(optional_plan_ids):
                    raise UserError(_('You cannot have an optional product that has a no common pricing\'s plan.'))

    def _get_pricelist_pricings(self, pricelist, product=None):
        self.ensure_one()
        is_template = not product and self._name == 'product.template'
        res = self.env['sale.subscription.plan']
        for pricing in self.product_subscription_pricing_ids.sorted(lambda x: not x.pricelist_id):
            if not pricing.plan_id.active:
                continue
            if pricing.pricelist_id and pricing.pricelist_id != pricelist:
                continue
            if not is_template and not pricing._applies_to(product or self):
                continue
            if pricing.plan_id not in res:
                yield pricing
                res |= pricing.plan_id

    def _website_can_be_added(self, pricelist=None, pricing=None, product=None):
        """ Return true if the product/template can be added to the active SO
        """
        self = product or self
        if not self.recurring_invoice:
            return True
        website = self.env['website'].get_current_website()
        so = website and request and website.sale_get_order()
        if not so or not so.plan_id:
            return True
        if pricing:
            return pricing.plan_id == so.plan_id and (not pricing.pricelist_id or pricing.pricelist_id == pricelist)
        return bool(self.env['sale.subscription.pricing'].sudo()._get_first_suitable_recurring_pricing(
            self, plan=so.plan_id, pricelist=pricelist or website.pricelist_id))

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        if not product_or_template.recurring_invoice:
            return res

        res['list_price'] = res['price']  # No pricelist discount for subscription prices
        currency = website.currency_id
        pricelist = website.pricelist_id
        requested_plan = request and request.params.get('plan_id')
        requested_plan = requested_plan and requested_plan.isdigit() and int(requested_plan)
        possible_pricing_count = 0

        pricings = []
        default_pricing = False
        for pricing in product_or_template.sudo()._get_pricelist_pricings(pricelist):
            price = pricing.price
            if pricing.currency_id != currency:
                price = pricing.currency_id._convert(
                    from_amount=price,
                    to_currency=currency,
                    company=self.env.company,
                    date=date,
                )

            if res.get('product_taxes', False):
                price = self.env['product.template']._apply_taxes_to_price(
                    price, currency, res['product_taxes'], res['taxes'], product_or_template,
                )

            price_format = format_amount(self.env, amount=price, currency=currency)
            pricing = {
                'plan_id': pricing.plan_id.id,
                'price': f"{pricing.plan_id.name}: {price_format}",
                'price_value': price,
                'table_price': price_format,
                'table_name': pricing.plan_id.name.replace(' ', ' '),
                'can_be_added': product_or_template._website_can_be_added(pricelist=pricelist, pricing=pricing)
            }
            possible_pricing_count += 1 if pricing['can_be_added'] else 0

            if (not default_pricing or pricing['plan_id'] == requested_plan) and pricing['can_be_added']:
                default_pricing = pricing
            pricings += [pricing]

        if pricings:
            plan_ids = self.env['sale.subscription.plan'].browse(pricing['plan_id'] for pricing in pricings)
            to_year = {'year': 1, 'month': 12, 'week': 52}
            translation_mapping = {'year': _('year'),
                                   'month': _('month'),
                                   'week': _('week'),
            }
            minimum_period = min(plan_ids.mapped('billing_period_unit'), key=lambda x: 1/to_year[x])
            for pricing in pricings:
                plan_id = plan_ids.browse(pricing['plan_id'])
                price = pricing['price_value'] / plan_id.billing_period_value * to_year[plan_id.billing_period_unit] \
                        / to_year[minimum_period]
                pricing['to_minimum_billing_period'] = f'{format_amount(self.env, amount=price, currency=currency)} / {translation_mapping.get(minimum_period, minimum_period)}'

        if not pricings:
            res.update({
                'is_subscription': True,
                'is_plan_possible': False,
                'pricings': [],
            })
            return res

        unit_price = default_pricing['price_value'] if default_pricing else 0
        return {
            **res,
            'is_subscription': True,
            'pricings': pricings,
            'is_plan_possible': possible_pricing_count > 0,
            'price': unit_price,
            'subscription_default_pricing_price': default_pricing['price'] if default_pricing else '',
            'subscription_default_pricing_plan_id': default_pricing['plan_id'] if default_pricing else False,
            'subscription_pricing_select': possible_pricing_count > 1,
            'prevent_zero_price_sale': website.prevent_zero_price_sale and currency.is_zero(
                unit_price,
            ),
            'temporal_unit_display': plan_ids.browse(default_pricing['plan_id']).billing_period_display_sentence if default_pricing else '',
        }

    # Search bar
    def _search_render_results_prices(self, mapping, combination_info):
        if not combination_info.get('is_subscription'):
            return super()._search_render_results_prices(mapping, combination_info)

        if not combination_info['is_plan_possible']:
            return '', 0

        return self.env['ir.ui.view']._render_template(
            'website_sale_subscription.subscription_search_result_price',
            values={
                'subscription_default_pricing_price': combination_info['subscription_default_pricing_price'],
            }
        ), 0

    def _get_sales_prices(self, website):
        prices = super()._get_sales_prices(website)
        pricelist = website.pricelist_id
        fiscal_position = website.fiscal_position_id.sudo()
        currency = pricelist.currency_id or self.env.company.currency_id
        date = fields.Date.context_today(self)
        website = self.env['website'].get_current_website()
        so = website and request and website.sale_get_order()
        plan_id = so and so.plan_id
        for template in self.filtered('recurring_invoice'):
            pricing = self.env['sale.subscription.pricing'].sudo()\
                ._get_first_suitable_recurring_pricing(template, plan=plan_id, pricelist=pricelist)
            if not pricing:
                prices[template.id].update({
                    'is_subscription': True,
                    'is_plan_possible': False,
                })
                continue

            unit_price = pricing.price

            # curr conversion
            if currency != pricing.currency_id:
                unit_price = pricing.currency_id._convert(
                    from_amount=unit_price,
                    to_currency=currency,
                    company=self.env.company,
                    date=date,
                )

            # taxes application
            product_taxes = template.sudo().taxes_id.filtered(lambda t: t.company_id == t.env.company)
            if product_taxes:
                taxes = fiscal_position.map_tax(product_taxes)
                unit_price = self.env['product.template']._apply_taxes_to_price(
                    unit_price, currency, product_taxes, taxes, template)

            plan = pricing.plan_id
            prices[template.id].update({
                'is_subscription': True,
                'price_reduce': unit_price,
                'is_plan_possible': template._website_can_be_added(
                    pricelist=pricelist, pricing=pricing),
                'temporal_unit_display': plan.billing_period_display_sentence,
            })
        return prices

    def _website_show_quick_add(self):
        self.ensure_one()
        return super()._website_show_quick_add() and self._website_can_be_added()

    def _can_be_added_to_cart(self):
        self.ensure_one()
        return super()._can_be_added_to_cart() and self._website_can_be_added()
