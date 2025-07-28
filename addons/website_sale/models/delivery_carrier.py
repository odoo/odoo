# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import fields, models


class DeliveryCarrier(models.Model):
    _name = 'delivery.carrier'
    _inherit = ['delivery.carrier', 'website.published.multi.mixin']

    website_description = fields.Text(
        string="Description for Online Quotations",
        related='product_id.description_sale',
        readonly=False,
    )

    def _prepare_best_delivery_by_country(self, product, pricelist_sudo, countries):
        """ Compute the info for the best delivery per country this product can be shipped to.

        :return: A dict per country the product can be shipped to. This dict uses the following
            schema: {
                'price': float, # the best possible price for the country
                'delivery_method': 'delivery.carrier', # the delivery method that will ship this
                                                       # product for the price
                'currency': 'res.currency', # the price currency
                'free_over_threshold': Optional[float], # optionnaly, the dict can contain the best
                                                        # free over threshold for the country
                'states': Optional['res.country.state'], # list of restricted states
            }
        :rtype: dict['res.country', dict[str, float | 'delivery.carrier' | 'res.country.state']]
        """
        # Creates a temporary order with a temporary partner to compute the shipping rates.
        tmp_partner = self.env['res.partner'].new({})
        tmp_order = self.env['sale.order'].new({
            'partner_id': tmp_partner.id,
            'pricelist_id': pricelist_sudo.id,
            'order_line': [{'product_id': product.id, 'product_uom_qty': 1.0}],
        })

        ResCountryState = self.env['res.country.state']
        best_delivery_by_country = defaultdict(lambda: {
            'price': float('inf'),
            'currency': tmp_order.currency_id,
            'states': ResCountryState,
        })
        all_filtered_countries = countries if any(not dm.country_ids for dm in self) else self.country_ids & countries
        states_per_country = dict(ResCountryState._read_group(
            domain=[('country_id', 'in', all_filtered_countries.ids)],
            groupby=['country_id'],
            aggregates=['id:recordset'],
        ))

        for dm in self:
            if dm.country_ids:
                filtered_countries = dm.country_ids & countries
            else:
                filtered_countries = countries
            for country in filtered_countries:
                # Filter only the states belonging to this country
                filtered_states = (
                    dm.state_ids & states_per_country.get(country, ResCountryState)
                    if dm.state_ids else []
                )
                tmp_partner.country_id = country
                # Only used to restrict on the address, therefore testing the first state is enough
                tmp_partner.state_id = filtered_states[:1]

                if not dm._match(tmp_partner, tmp_order):
                    continue
                shipment_rate = dm.rate_shipment(tmp_order)
                if not shipment_rate['success']:
                    continue
                if shipment_rate['price'] < best_delivery_by_country[country]['price']:
                    best_delivery_by_country[country].update(
                        price=shipment_rate['price'], delivery_method=dm, states=filtered_states,
                    )
                if (
                    dm.free_over
                    and dm.amount < best_delivery_by_country[country].get(
                        'free_over_threshold', float('inf'),
                    )
                ):
                    best_delivery_by_country[country]['free_over_threshold'] = dm.amount

        return best_delivery_by_country
