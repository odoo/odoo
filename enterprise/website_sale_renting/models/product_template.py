# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from math import ceil
from pytz import timezone, UTC

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import format_amount

from odoo.addons.sale_renting.models.product_pricing import PERIOD_RATIO


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _get_additionnal_combination_info(self, product_or_template, quantity, date, website):
        """Override to add the information about renting for rental products

        If the product is rent_ok, this override adds the following information about the rental:
            - is_rental: Whether combination is rental,
            - rental_duration: The duration of the first defined product pricing on this product
            - rental_unit: The unit of the first defined product pricing on this product
            - default_start_date: If no pickup nor rental date in context, the start_date of the
                                   first renting sale order line in the cart;
            - default_end_date: If no pickup nor rental date in context, the end_date of the
                                   first renting sale order line in the cart;
            - current_rental_duration: If no pickup nor rental date in context, see rental_duration,
                                       otherwise, the duration between pickup and rental date in the
                                       current_rental_unit unit.
            - current_rental_unit: If no pickup nor rental date in context, see rental_unit,
                                   otherwise the unit of the best pricing for the renting between
                                   pickup and rental date.
            - current_rental_price: If no pickup nor rental date in context, see price,
                                    otherwise the price of the best pricing for the renting between
                                    pickup and rental date.
        """
        res = super()._get_additionnal_combination_info(product_or_template, quantity, date, website)

        if not product_or_template.rent_ok:
            return res

        res['list_price'] = res['price']  # No pricelist discount for rental prices
        currency = website.currency_id
        pricelist = website.pricelist_id
        ProductPricing = self.env['product.pricing']

        pricing = ProductPricing._get_first_suitable_pricing(product_or_template, pricelist)
        if not pricing:
            return res

        # Compute best pricing rule or set default
        order = website.sale_get_order() if website and request else self.env['sale.order']
        start_date = self.env.context.get('start_date') or order.rental_start_date
        end_date = self.env.context.get('end_date') or order.rental_return_date
        if start_date and end_date:
            current_pricing = product_or_template._get_best_pricing_rule(
                start_date=start_date,
                end_date=end_date,
                pricelist=pricelist,
                currency=currency,
            )
            current_unit = current_pricing.recurrence_id.unit
            current_duration = ProductPricing._compute_duration_vals(
                start_date, end_date
            )[current_unit]
        else:
            current_unit = pricing.recurrence_id.unit
            current_duration = pricing.recurrence_id.duration
            current_pricing = pricing

        # Compute current price

        # Here we don't add the current_attributes_price_extra nor the
        # no_variant_attributes_price_extra to the context since those prices are not added
        # in the context of rental.
        current_price = pricelist._get_product_price(
            product=product_or_template,
            quantity=quantity,
            currency=currency,
            start_date=start_date,
            end_date=end_date,
        )

        default_start_date, default_end_date = self._get_default_renting_dates(
            start_date, end_date, current_duration, current_unit
        )

        ratio = ceil(current_duration) / pricing.recurrence_id.duration if pricing.recurrence_id.duration else 1
        if current_unit != pricing.recurrence_id.unit:
            ratio *= PERIOD_RATIO[current_unit] / PERIOD_RATIO[pricing.recurrence_id.unit]

        # apply taxes
        product_taxes = res['product_taxes']
        if product_taxes:
            current_price = self.env['product.template']._apply_taxes_to_price(
                current_price, currency, product_taxes, res['taxes'], product_or_template,
            )

        suitable_pricings = ProductPricing._get_suitable_pricings(product_or_template, pricelist)

        # If there are multiple pricings with the same recurrence, we only keep the cheapest ones
        best_pricings = {}
        for p in suitable_pricings:
            if p.recurrence_id not in best_pricings:
                best_pricings[p.recurrence_id] = p
            elif best_pricings[p.recurrence_id].price > p.price:
                best_pricings[p.recurrence_id] = p

        suitable_pricings = best_pricings.values()
        def _pricing_price(pricing):
            if product_taxes:
                price = self.env['product.template']._apply_taxes_to_price(
                    pricing.price, currency, product_taxes, res['taxes'], product_or_template
                )
            else:
                price = pricing.price
            if pricing.currency_id == currency:
                return price
            return pricing.currency_id._convert(
                from_amount=price,
                to_currency=currency,
                company=self.env.company,
                date=date,
            )
        pricing_table = [
            (p.name, format_amount(self.env, _pricing_price(p), currency))
            for p in suitable_pricings
        ]
        recurrence = pricing.recurrence_id

        return {
            **res,
            'is_rental': True,
            'rental_duration': recurrence.duration,
            'rental_duration_unit': recurrence.unit,
            'rental_unit': recurrence._get_unit_label(recurrence.duration),
            'default_start_date': default_start_date,
            'default_end_date': default_end_date,
            'current_rental_duration': ceil(current_duration),
            'current_rental_unit': current_pricing.recurrence_id._get_unit_label(current_duration),
            'current_rental_price': current_price,
            'current_rental_price_per_unit': current_price / (ratio or 1),
            'base_unit_price': 0,
            'base_unit_name': False,
            'pricing_table': pricing_table,
            'prevent_zero_price_sale': website.prevent_zero_price_sale and currency.is_zero(
                current_price,
            ),
        }

    @api.model
    def _get_default_renting_dates(self, start_date, end_date, duration, unit):
        """ Get default renting dates to help user

        :param datetime start_date: a start_date which is directly returned if defined
        :param datetime end_date: a end_date which is directly returned if defined
        :param int duration: the duration expressed in int, in the unit given
        :param string unit: The duration unit, which can be 'hour', 'day', 'week' or 'month'
        """
        if start_date and end_date and start_date >= end_date:
            raise UserError(_("Please choose a return date that is after the pickup date."))

        if start_date or end_date:
            return start_date, end_date

        default_start_dt = self._get_default_start_date()
        if unit == 'hour':
            default_end_dt = self._get_default_end_date(default_start_dt, duration, unit)
        else:
            # If unit in day, week, month, take into account the entire day.
            # 21st + 1 day --> from 21st 00:00:00 to 22nd 23:59:59
            default_start_dt = datetime.combine(default_start_dt.date(), datetime.min.time())
            # remove a second to avoid adding a day (from date point of view)
            default_end_dt = self._get_default_end_date(default_start_dt + relativedelta(seconds=-1), duration, unit)
            # Consider the timezone if frontend request
            # Return the UTC value according to the client
            # because the frontend will convert values according to its timezone
            # (and without conversion, we risk changing day).
            if request and request.is_frontend and request.cookies.get('tz'):
                client_tz = timezone(request.cookies['tz'])
                default_start_dt = client_tz.localize(default_start_dt).astimezone(UTC)
                default_end_dt = client_tz.localize(default_end_dt).astimezone(UTC)
        return default_start_dt, default_end_dt

    @api.model
    def _get_default_start_date(self):
        """ Get the default pickup date and make it extensible """
        return self._get_first_potential_date(
            fields.Datetime.now() + relativedelta(days=1, hours=1, minute=0, second=0, microsecond=0)
        )

    @api.model
    def _get_default_end_date(self, start_date, duration, unit):
        """ Get the default return date based on pickup date and duration

        :param datetime start_date: the default start_date
        :param int duration: the duration expressed in int, in the unit given
        :param string unit: The duration unit, which can be 'hour', 'day', 'week' or 'month'
        """
        return self._get_first_potential_date(max(
            start_date + relativedelta(**{f'{unit}s': duration}),
            start_date + self.env.company._get_minimal_rental_duration()
        ))

    @api.model
    def _get_first_potential_date(self, date):
        """ Get the first potential date which respects company unavailability days settings
        """
        days_forbidden = self.env.company._get_renting_forbidden_days()
        weekday = date.isoweekday()
        for i in range(7):
            if ((weekday + i) % 7 or 7) not in days_forbidden:
                break
        return date + relativedelta(days=i)

    def _search_render_results_prices(self, mapping, combination_info):
        if not combination_info.get('is_rental'):
            return super()._search_render_results_prices(mapping, combination_info)

        return self.env['ir.ui.view']._render_template(
            'website_sale_renting.rental_search_result_price',
            values={
                'currency': mapping['detail']['display_currency'],
                'price': combination_info['price'],
                'duration': combination_info['rental_duration'],
                'unit': combination_info['rental_unit'],
            }
        ), None

    def _get_sales_prices(self, website):
        prices = super()._get_sales_prices(website)
        pricelist = website.pricelist_id

        for template in self:
            if not template.rent_ok:
                continue
            pricing = self.env['product.pricing']._get_first_suitable_pricing(template, pricelist)
            if pricing:
                recurrence = pricing.recurrence_id
                prices[template.id]['rental_duration'] = recurrence.duration
                prices[template.id]['rental_unit'] = recurrence._get_unit_label(recurrence.duration)
            else:
                prices[template.id]['rental_duration'] = 0
                prices[template.id]['rental_unit'] = False

        return prices

    def _search_get_detail(self, website, order, options):
        search_details = super()._search_get_detail(website, order, options)
        if options.get('rent_only') or (options.get('from_date') and options.get('to_date')):
            search_details['base_domain'].append([('rent_ok', '=', True)])
        return search_details

    def _can_be_added_to_cart(self):
        """Override to allow rental products to be used in a sale order"""
        return super()._can_be_added_to_cart() or self.rent_ok

    def _website_show_quick_add(self):
        self.ensure_one()
        website = self.env['website'].get_current_website()
        return super()._website_show_quick_add() or (
            self.rent_ok and (not website.prevent_zero_price_sale or self._get_contextual_price())
        )
