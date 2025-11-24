# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.fields import Domain


class ResPartner(models.Model):
    _inherit = 'res.partner'

    wishlist_ids = fields.One2many(
        string="Wishlist",
        comodel_name='product.wishlist',
        inverse_name='partner_id',
        domain=[('active', '=', True)],
    )
    pickup_delivery_carrier_id = fields.Many2one('delivery.carrier', ondelete='cascade')  # The delivery method that generated this pickup location.
    pickup_location_data = fields.Json()  # Technical field: information needed by shipping providers in case of pickup point addresses.

    @api.onchange('property_product_pricelist')
    def _onchange_property_product_pricelist(self):
        open_order = self.env['sale.order'].sudo().search([
            ('partner_id', '=', self._origin.id),
            ('pricelist_id', '=', self._origin.property_product_pricelist.id),
            ('pricelist_id', '!=', self.property_product_pricelist.id),
            ('website_id', '!=', False),
            ('state', '=', 'draft'),
        ], limit=1)

        if open_order:
            return {'warning': {
                'title': _('Open Sale Orders'),
                'message': _(
                    "This partner has an open cart. "
                    "Please note that the pricelist will not be updated on that cart. "
                    "Also, the cart might not be visible for the customer until you update the pricelist of that cart."
                ),
            }}

    def _get_current_partner(self, *, order_sudo=False, **kwargs):
        """ Override `portal` to get current partner from order_sudo if user is not signed up. """
        if order_sudo:
            return (
                (not order_sudo._is_anonymous_cart() and order_sudo.partner_id)
                or self.env['res.partner'] # Avoid returning public user's partner
            )
        return super()._get_current_partner(order_sudo=order_sudo, **kwargs)

    def _get_frontend_writable_fields(self):
        """ Override `portal` to make website whitelist fields writable in portal address. """
        frontend_writable_fields = super()._get_frontend_writable_fields()
        frontend_writable_fields.update(
            self.env['ir.model']._get('res.partner')._get_form_writable_fields().keys()
        )

        return frontend_writable_fields

    def _get_order_fiscal_position_recompute_domain(self):
        """Return a domain of sale orders for which we should recompute fiscal position after address update."""
        return Domain([
            ('state', '=', 'draft'),
            ('website_id', '!=', False),
            '|', ('partner_id', 'in', self.ids),
                 ('partner_shipping_id', 'in', self.ids),
        ])

    def _get_delivery_address_domain(self):
        return super()._get_delivery_address_domain() & Domain('pickup_delivery_carrier_id', '=', False)

    def _is_address_usable(self):
        """ Override to prevent using pickup locations as regular delivery addresses. """
        return super()._is_address_usable() and not self.pickup_delivery_carrier_id

    @api.model
    def _address_from_json(self, json_location_data, parent_id, pickup_delivery_carrier_id=False):
        """ Searches for an existing address with the same data as the one in json_location_data
        and the same parent_id. If no address is found, creates a new one.

        :param dict json_location_data: The location data in JSON format returned by the carrier's API.
        :param res.partner parent_id: The parent partner of the address to create.
        :param str pickup_delivery_carrier_id: The type of the delivery method that generated this pickup location.
        :return: The existing or newly created address.
        :rtype: res.partner
        """
        if json_location_data:
            name = json_location_data.get('name', False)
            street = json_location_data.get('street', False)
            city = json_location_data.get('city', False)
            zip_code = json_location_data.get('zip_code', False)
            country_code = json_location_data.get('country_code', False)
            country = self.env['res.country'].search([('code', '=', country_code)]).id
            state = self.env['res.country.state'].search([
                ('code', '=', json_location_data.get('state', False)),
                ('country_id', '=', country),
            ]).id if (json_location_data.get('state') and country) else None
            email = json_location_data.get('email', parent_id.email)
            phone = json_location_data.get('phone', parent_id.phone)

            domain = [
                ('name', '=', name),
                ('street', '=', street),
                ('city', '=', city),
                ('state_id', '=', state),
                ('country_id', '=', country),
                ('type', '=', 'delivery'),
                ('parent_id', '=', parent_id.id),
                ('pickup_delivery_carrier_id', '=', pickup_delivery_carrier_id)
            ]
            existing_partner = self.env['res.partner'].with_context(active_test=False).search(domain, limit=1)
            if existing_partner:
                return existing_partner
            else:
                return self.env['res.partner'].create({
                    'parent_id': parent_id.id,
                    'type': 'delivery',
                    'name': name,
                    'street': street,
                    'city': city,
                    'state_id': state,
                    'zip': zip_code,
                    'country_id': country,
                    'email': email,
                    'phone': phone,
                    'pickup_delivery_carrier_id': pickup_delivery_carrier_id,
                    'pickup_location_data': json_location_data,
                    'active': False,
                })
        return self.env['res.partner']

    def write(self, vals):
        res = super().write(vals)
        if {'country_id', 'vat', 'zip'} & vals.keys() and self:
            # Recompute fiscal position for open website orders
            order_fpos_recompute_domain = self._get_order_fiscal_position_recompute_domain()
            if orders_sudo := self.env['sale.order'].sudo().search(order_fpos_recompute_domain):
                orders_by_fpos = orders_sudo.grouped('fiscal_position_id')
                self.env.add_to_compute(orders_sudo._fields['fiscal_position_id'], orders_sudo)
                if fpos_changed := orders_sudo.filtered(
                    lambda so: so not in orders_by_fpos.get(so.fiscal_position_id, []),
                ):
                    fpos_changed._recompute_taxes()
                    # other modules may extend the orders to recompute for
                    # non-draft orders (for ex. sale_subscription), we need
                    # to ensure to only recompute prices for draft orders
                    fpos_changed.filtered(lambda order: order.state == 'draft')._recompute_prices()
        for key in ['phone', 'email']:
            if key in vals:
                for partner in self:
                    children = self.env['res.partner'].with_context(active_test=False).search([('parent_id', '=', partner.id), ('type', '=', 'delivery'), ('pickup_delivery_carrier_id', '!=', False)])
                    children.write({key: vals[key]})
        return res
