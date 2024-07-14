# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
import requests

from datetime import timedelta

from odoo import fields, models, _
from odoo.exceptions import ValidationError

from .shiprocket_request import ShipRocket

_logger = logging.getLogger(__name__)


class DeliverCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(
        selection_add=[('shiprocket', 'Shiprocket')],
        ondelete={'shiprocket': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})}
    )
    shiprocket_email = fields.Char(string="Shiprocket Email",
                                   help="Enter your Username from Shiprocket account (API).")
    shiprocket_password = fields.Char(string="Shiprocket Password",
                                      help="Enter your Password from Shiprocket account (API).")
    shiprocket_access_token = fields.Text(
        string="Shiprocket Access Token",
        help="Generate access token using Shiprocket credentials", copy=False
    )
    shiprocket_token_valid_upto = fields.Datetime(
        string="Token Expiry", copy=False,
        help="Shiprocket token expires in 10 days. Token will be auto generate based on this token expiry date."
    )
    shiprocket_channel_id = fields.Many2one(
        'shiprocket.channel',
        string="Shiprocket Channel",
        domain="[('shiprocket_email', '=', shiprocket_email)]",
        help="Get all the integrated channels from your Shiprocket account."
             "This channel id is used to select or specify a custom channel at the time of Shiprocket order creation."
    )
    shiprocket_courier_ids = fields.Many2many(
        'shiprocket.courier',
        string="Shiprocket Couriers", copy=False,
        domain="[('shiprocket_email', '=', shiprocket_email)]",
        help="Get all the integrated Couriers from your Shiprocket account."
             "Based on the courier selections the rate will be fetched from the Shiprocket."
    )
    shiprocket_default_package_type_id = fields.Many2one(
        "stock.package.type",
        string="Package Type",
        help="Shiprocket requires package dimensions for getting accurate rate, "
             "you can define these in a package type that you set as default"
    )
    shiprocket_payment_method = fields.Selection(
        [('prepaid', 'Prepaid'), ('cod', 'COD')],
        default="prepaid",
        string="Payment Method",
        help="The method of payment. Can be either COD (Cash on delivery) Or Prepaid while creating Shiprocket order."
    )
    shiprocket_manifests_generate = fields.Boolean(
        string="Generate Manifest",
        help="A manifest is a document that is required by some carriers to streamline the pickup process."
             "particularly when shipping out a high-volume of ecommerce orders."
    )
    shiprocket_pickup_request = fields.Boolean(
        string="Pickup Request", default=True,
        help="Create a pickup request for your order shipment using Validate button of the Delivery Order."
    )

    def action_shiprocket_test_connection(self):
        """
        Test connection by generate access token from shiprocket email and password.
        """
        self.ensure_one()
        if self.delivery_type == 'shiprocket':
            sr = ShipRocket(self, self.log_xml)
            response_json = sr._authorize_generate_token()
            if response_json.get('token'):
                self.write({
                    'shiprocket_access_token': response_json['token'],
                    'shiprocket_token_valid_upto': fields.datetime.now() + timedelta(days=9)
                })
                message_type = 'success'
                message = _("Access token is generated successfully!")
            else:
                if response_json.get('message'):
                    error_message = response_json['message']
                else:
                    error_message = _("Authentication failed! Please check your credentials.")
                message_type = 'danger'
                message = error_message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Shiprocket Notification"),
                    'type': message_type,
                    'message': message,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def action_get_channels(self):
        """
        Fetch the dictionary of channel(s) configured by the customer on its
        shiprocket account and create shiprocket channel record(s) in odoo.
        """
        for carrier in self:
            if carrier.delivery_type != 'shiprocket':
                continue
            sr = ShipRocket(carrier, self.log_xml)
            channels = sr._fetch_shiprocket_channels()
            if not channels:
                raise ValidationError(_('Failed to fetch Shiprocket Channel(s), Please try again later.'))
            # multiple shipping method(s) can use same channels
            current_channels = self.env['shiprocket.channel'].search([('shiprocket_email', '=', carrier.shiprocket_email)])
            new_channel_vals = []
            for name, code in channels.items():
                existing_channels = current_channels.filtered(lambda c: c.channel_code == code)
                # remove channel if already exists
                current_channels -= existing_channels
                if not existing_channels:
                    new_channel_vals.append({
                        'name': name,
                        'channel_code': code,
                        'shiprocket_email': carrier.shiprocket_email
                    })
            if new_channel_vals:
                self.env['shiprocket.channel'].create(new_channel_vals)
            # delete channel(s) if not exists anymore
            current_channels.unlink()

    def action_get_couriers(self):
        """
        Fetch shiprocket carriers from shiprocket account.
        create record(s) of shiprocket courier(s) in odoo.
        """
        for carrier in self:
            if carrier.delivery_type != 'shiprocket':
                continue
            sr = ShipRocket(carrier, self.log_xml)
            couriers_list = sr._fetch_shiprocket_couriers()
            if not couriers_list:
                raise ValidationError(_('Failed to fetch Shiprocket Couriers(s), Please try again later.'))
            # multiple shipping method(s) can use same couriers
            current_couriers = self.env['shiprocket.courier'].search([('shiprocket_email', '=', carrier.shiprocket_email)])
            new_courier_vals = []
            for courier in couriers_list:
                existing_couriers = current_couriers.filtered(lambda c: c.courier_code == courier.get('id'))
                # remove courier if already exists
                current_couriers -= existing_couriers
                if not existing_couriers:
                    new_courier_vals.append({
                        'name': courier.get('name'),
                        'courier_code': courier.get('id'),
                        'shiprocket_email': carrier.shiprocket_email
                    })
            if new_courier_vals:
                self.env['shiprocket.courier'].create(new_courier_vals)
            # delete courier(s) if not exists anymore
            current_couriers.unlink()

    def _shiprocket_convert_weight(self, weight):
        """
        Returns the weight in KG for a shiprocket order.
        """
        self.ensure_one()
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)

    def _shiprocket_converted_amount(self, order, price_inr):
        """
        Returns the converted amount from the INR amount based on order's currency.
        """
        return self.env.ref('base.INR')._convert(
            price_inr,
            order.currency_id,
            order.company_id,
            fields.Date.context_today(self)
        )

    def shiprocket_rate_shipment(self, order):
        """
        Returns shipping rate for the order and chosen shipping method.
        """
        sr = ShipRocket(self, self.log_xml)
        result = sr._rate_request(
            order.partner_shipping_id,
            order.warehouse_id.partner_id or order.warehouse_id.company_id.partner_id,
            order
        )
        if result.get('error_found'):
            return {'success': False, 'price': 0.0, 'error_message': result['error_found'], 'warning_message': False}
        price = float(result.get('price'))
        if order.currency_id.id != self.env.ref('base.INR').id:
            price = self._shiprocket_converted_amount(order, price)
        return {
            'success': True,
            'price': price,
            'error_message': False,
            'warning_message': result.get('warning_message')
        }

    def shiprocket_send_shipping(self, pickings):
        """
        Send shipment to shiprocket. Once the shiprocket order is
        generated, it will post the message(s) with tracking link,
        shipping label pdf and manifest pdf.
        """
        sr = ShipRocket(self, self.log_xml)
        def _get_document_data(url):
            """ Returns the document content for label and manifest. """
            try:
                document_response = requests.get(url, timeout=30)
                document_response.raise_for_status()
                _logger.info('Document downloaded successfully from %s', url)
                return document_response.content
            except requests.exceptions.HTTPError as e:
                _logger.warning('Document download failed from %s - %s', url, e)
            except requests.exceptions.ConnectionError as e:
                _logger.warning('Connection error while downloading %s - %s', url, e)
        res = []
        for picking in pickings:
            shippings = sr._send_shipping(picking)
            picking.shiprocket_orders = " + ".join(shippings.get('order_ids'))
            res.append({
                'tracking_number': " + ".join(shippings.get('tracking_numbers')),
                'exact_price': shippings.get('exact_price')
            })
            for pack in shippings['all_pack'].values():
                response = pack.get('response')
                courier_name = response.get('courier_name')
                carrier_tracking_ref = response.get('awb_code')
                if response.get('warning_message'):
                    picking.message_post(body='%s' % (response['warning_message']))
                if response.get('label_url'):
                    label_data = _get_document_data(response['label_url'])
                    attachments = [("%s-%s.pdf" % (courier_name, carrier_tracking_ref), label_data)]
                    log_message = _("Label generated of %s with Tracking Number: %s",
                                    courier_name, carrier_tracking_ref)
                    picking.message_post(body=log_message, attachments=attachments)
                # if shiprocket_pickup_request is enable then only shiprocket generate manifest(s).
                if self.shiprocket_manifests_generate and response.get('manifest_url'):
                    manifest_data = _get_document_data(response['manifest_url'])
                    attachments = [("Manifest - %s-%s.pdf" % (courier_name, carrier_tracking_ref), manifest_data)]
                    log_message = _("Manifest generated of %s", courier_name)
                    picking.message_post(body=log_message, attachments=attachments)
            # when carrier is in test mode, need to cancel shiprocket order.
            if not self.prod_environment:
                # Need carrier_tracking_ref to cancel shipment
                picking.carrier_tracking_ref = " + ".join(shippings.get('tracking_numbers'))
                self.shiprocket_cancel_shipment(picking)
        return res

    def shiprocket_get_tracking_link(self, picking):
        """
        Returns the tracking links for a picking.
        Shiprocket returns one tracking link for one package.
        """
        tracking_urls = []
        tracking_numbers = picking.carrier_tracking_ref and picking.carrier_tracking_ref.split(' + ') or []
        for tracking_number in tracking_numbers:
            track_url = (str(tracking_number), "https://shiprocket.co/tracking/%s" % (tracking_number))
            tracking_urls.append(track_url)
        return len(tracking_urls) == 1 and tracking_urls[0][1] or json.dumps(tracking_urls)

    def shiprocket_cancel_shipment(self, picking):
        """
        Cancel shipment using shiprocket requests.
        To Refunds for canceled shipment(s) or order(s) will be promptly processed:
        - Cancel the Shiprocket order(s), if pickup request enable.
        - Cancel the Shiprocket shipment(s), if pickup request disable.
        post message if order is already canceled.
        """
        sr = ShipRocket(self, self.log_xml)
        pickup_request = picking.carrier_id.shiprocket_pickup_request
        shiprocket_orders = []
        if pickup_request:
            if not picking.shiprocket_orders:
                picking.message_post(body=_('Shiprocket order(s) not found to cancel the shipment!'))
            else:
                shiprocket_orders = picking.shiprocket_orders.split(' + ')
        elif not picking.carrier_tracking_ref:
            picking.message_post(body=_('AWB number(s) not found to cancel the shipment!'))
        else:
            shiprocket_orders = picking.carrier_tracking_ref.split(' + ')
        if shiprocket_orders:
            cancel_order = sr._send_cancelling(shiprocket_orders, pickup_request=pickup_request)
            for order, response in cancel_order.items():
                if response.get('status') == 200 or response.get('message'):
                    msg = 'Order #' if pickup_request else 'AWB #'
                    msg += order + ' - ' + response.get('message') or _('Order canceled successfully!')
                    picking.message_post(body=msg)
        # To avoid the duplicates values in Tracking Reference
        if not self.prod_environment:
            picking.carrier_tracking_ref = ''
