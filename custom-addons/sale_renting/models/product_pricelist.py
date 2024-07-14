# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    product_pricing_ids = fields.One2many(
        comodel_name='product.pricing',
        inverse_name='pricelist_id',
        string="Renting Price Rules",
        domain=['|', ('product_template_id', '=', None), ('product_template_id.active', '=', True)],
    )

    @api.constrains('product_pricing_ids')
    def _check_pricing_product_rental(self):
        for pricing in self.product_pricing_ids:
            if not pricing.product_template_id.rent_ok:
                raise UserError(_(
                    "You can not have a time-based rule for products that are not rentable."
                ))

    def _compute_price_rule(
        self, products, quantity, currency=None, date=False, start_date=None, end_date=None,
        **kwargs
    ):
        """ Override to handle the rental product price

        Note that this implementation can be done deeper in the base price method of pricelist item
        or the product price compute method.
        """
        self and self.ensure_one()  # self is at most one record

        currency = currency or self.currency_id or self.env.company.currency_id
        currency.ensure_one()

        if not products:
            return {}

        if not date:
            # Used to fetch pricelist rules and currency rates
            date = fields.Datetime.now()

        results = {}
        if self._enable_rental_price(start_date, end_date):
            rental_products = products.filtered('rent_ok')
            Pricing = self.env['product.pricing']
            for product in rental_products:
                if start_date and end_date:
                    pricing = product._get_best_pricing_rule(
                        start_date=start_date, end_date=end_date, pricelist=self, currency=currency
                    )
                    duration_vals = Pricing._compute_duration_vals(start_date, end_date)
                    duration = pricing and duration_vals[pricing.recurrence_id.unit or 'day'] or 0
                else:
                    pricing = Pricing._get_first_suitable_pricing(product, self)
                    duration = pricing.recurrence_id.duration

                if pricing:
                    price = pricing._compute_price(duration, pricing.recurrence_id.unit)
                elif product._name == 'product.product':
                    price = product.lst_price
                else:
                    price = product.list_price
                results[product.id] = pricing.currency_id._convert(
                    price, currency, self.env.company, date
                ), False

        price_computed_products = self.env[products._name].browse(results.keys())
        return {
            **results,
            **super()._compute_price_rule(
                products - price_computed_products, quantity, currency=currency, date=date, **kwargs
            ),
        }

    def _enable_rental_price(self, start_date, end_date):
        """ Enable the rental price computing or use the default price computing

        :param date start_date: A rental pickup date
        :param date end_date: A rental return date
        :return: Whether product pricing should be or not be used to compute product price
        """
        return (start_date and end_date)
