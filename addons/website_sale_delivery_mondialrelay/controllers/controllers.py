# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.addons.website_sale.controllers.main import WebsiteSale, PaymentPortal
from odoo.addons.website_sale_delivery.controllers.main import WebsiteSaleDelivery

from odoo.exceptions import AccessDenied, ValidationError, UserError
from odoo.http import request


class MondialRelay(http.Controller):

    @http.route(['/website_sale_delivery_mondialrelay/update_shipping'], type='json', auth="public", website=True)
    def mondial_relay_update_shipping(self, **data):
        order = request.website.sale_get_order()

        if order.partner_id == request.website.user_id.sudo().partner_id:
            raise AccessDenied('Customer of the order cannot be the public user at this step.')

        if order.carrier_id.country_ids:
            country_is_allowed = data['Pays'][:2].upper() in order.carrier_id.country_ids.mapped(lambda c: c.code.upper())
            assert country_is_allowed, _("%s is not allowed for this delivery carrier.", data['Pays'])

        partner_shipping = order.partner_id.sudo()._mondialrelay_search_or_create({
            'id': data['ID'],
            'name': data['Nom'],
            'street': data['Adresse1'],
            'street2': data['Adresse2'],
            'zip': data['CP'],
            'city': data['Ville'],
            'country_code': data['Pays'][:2].lower(),
        })
        if order.partner_shipping_id != partner_shipping:
            order.partner_shipping_id = partner_shipping
            order.onchange_partner_shipping_id()

        return {
            'address': request.env['ir.qweb']._render('website_sale.address_on_payment', {
                'order': order,
                'only_services': order and order.only_services,
            }),
            'new_partner_shipping_id': order.partner_shipping_id.id,
        }


class WebsiteSaleMondialrelay(WebsiteSale):

    @http.route()
    def address(self, **kw):
        res = super().address(**kw)
        Partner_sudo = request.env['res.partner'].sudo()
        partner_id = res.qcontext.get('partner_id', 0)
        if partner_id > 0 and Partner_sudo.browse(partner_id).is_mondialrelay:
            raise UserError(_('You cannot edit the address of a Point Relais®.'))
        return res


class WebsiteSaleDeliveryMondialrelay(WebsiteSaleDelivery):

    def _update_website_sale_delivery_return(self, order, **post):
        res = super()._update_website_sale_delivery_return(order, **post)
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


class PaymentPortalMondialRelay(PaymentPortal):

    @http.route()
    def shop_payment_transaction(self, *args, **kwargs):
        order = request.website.sale_get_order()
        if order.partner_shipping_id.is_mondialrelay and order.carrier_id and not order.carrier_id.is_mondialrelay and order.delivery_set:
            raise ValidationError(_('Point Relais® can only be used with the delivery method Mondial Relay.'))
        elif not order.partner_shipping_id.is_mondialrelay and order.carrier_id.is_mondialrelay:
            raise ValidationError(_('Delivery method Mondial Relay can only ship to Point Relais®.'))
        return super().shop_payment_transaction(*args, **kwargs)
