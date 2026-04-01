# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, http
from odoo.exceptions import AccessDenied, UserError
from odoo.http import request

from odoo.addons.website_sale.controllers.delivery import Delivery
from odoo.addons.website_sale.controllers.main import WebsiteSale


class MondialRelay(http.Controller):

    @http.route(['/website_sale_mondialrelay/update_shipping'], type='jsonrpc', auth="public", website=True)
    def mondial_relay_update_shipping(self, **data):
        order_sudo = request.cart

        if order_sudo._is_anonymous_cart():
            raise AccessDenied(self.env._('Customer of the order cannot be the public user at this step.'))

        if order_sudo.carrier_id.country_ids:
            country_is_allowed = data['Pays'][:2].upper() in order_sudo.carrier_id.country_ids.mapped(lambda c: c.code.upper())
            assert country_is_allowed, _("%s is not allowed for this delivery carrier.", data['Pays'])

        partner_shipping = order_sudo.partner_id.sudo()._mondialrelay_search_or_create({
            'id': data['ID'],
            'name': data['Nom'],
            'street': data['Adresse1'],
            'street2': data['Adresse2'],
            'zip': data['CP'],
            'city': data['Ville'],
            'country_code': data['Pays'][:2].lower(),
            'phone': order_sudo.partner_id.phone,
        })
        if order_sudo.partner_shipping_id != partner_shipping:
            order_sudo.partner_shipping_id = partner_shipping

        return {
            'address': request.env['ir.qweb']._render('website_sale.address_on_checkout', {
                'order': order_sudo,
                'only_services': order_sudo.only_services,
            }),
            'new_partner_shipping_id': order_sudo.partner_shipping_id.id,
        }


class WebsiteSaleMondialrelay(WebsiteSale):

    def _prepare_address_update(self, *args, **kwargs):
        """Updates of mondialrelay addresses are forbidden"""
        partner_sudo, _address_type = super()._prepare_address_update(*args, **kwargs)

        if partner_sudo and partner_sudo.is_mondialrelay:
            raise UserError(_('You cannot edit the address of a Point Relais®.'))

        return partner_sudo, _address_type

    def _check_delivery_address(self, partner_sudo):
        # skip check for mondialrelay partners as the customer can not edit them
        if partner_sudo.is_mondialrelay:
            return True
        return super()._check_delivery_address(partner_sudo)


class WebsiteSaleDeliveryMondialrelay(Delivery):

    def _order_summary_values(self, order, **post):
        res = super()._order_summary_values(order, **post)
        if order.carrier_id.is_mondialrelay:
            res['mondial_relay'] = {
                'brand': order.carrier_id.mondialrelay_brand,
                'col_liv_mod': order.carrier_id.mondialrelay_packagetype,
                'partner_zip': order.partner_shipping_id.zip,
                'partner_country_code': order.partner_shipping_id.country_id.code.upper(),
                'allowed_countries': ','.join(order.carrier_id.country_ids.mapped('code')).upper(),
            }
            if order.partner_shipping_id.is_mondialrelay:
                res['mondial_relay']['current'] = '%s-%s' % (
                    res['mondial_relay']['partner_country_code'],
                    order.partner_shipping_id.ref.lstrip('MR#'),
                )

        return res
