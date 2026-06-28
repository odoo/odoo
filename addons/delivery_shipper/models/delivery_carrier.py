# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from markupsafe import Markup
from odoo.exceptions import UserError
from .shipper_service import Shipper
import logging
import math

logger = logging.getLogger(__name__)


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('shipper', 'Shipper'),
    ], ondelete={'shipper': lambda records: records.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    shipper_api_key = fields.Char(help='Shipper API Integration key')
    shipper_default_package_type_id = fields.Many2one(
        'stock.package.type',
        string='Default Package Type for Shipper',
        help='Package dimensions are required to get more accurate rates. You can define these in a package type that you set as default',
    )
    shipper_origin_address = fields.Many2one(
        string="Origin Address",
        help="This address will be used when fetching the available services from shipper.",
        comodel_name='res.partner',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=lambda self: self.env.company.partner_id,
    )
    shipper_3pl_partner = fields.Selection([
        ('57', 'J&T - Regular'),
        ('228', 'Ninja Xpress - Regular'),
        ('349', 'SAP - Regular'),
        ('58', 'SiCepat - Regular'),
        ('562', 'Anteraja - Regular'),
        ('1', 'JNE - Regular'),
        ('564', 'Anteraja - Express'),
        ('59', 'SiCepat - Express'),
        ('2', 'JNE - Express'),
    ], string="Shipper 3PL Partners")
    shipper_3pl_partner_id = fields.Integer(compute='_compute_shipper_3pl_partner_id', store=True)

    @api.depends('shipper_3pl_partner')
    def _compute_shipper_3pl_partner_id(self):
        for record in self:
            record.shipper_3pl_partner_id = int(record.shipper_3pl_partner) if record.shipper_3pl_partner else 0

    # Shipping Carrier Methods
    # TODO: Add an option for using geolocation instead; maybe
    def shipper_rate_shipment(self, order):
        shipper = self._get_shipper()
        origin_area_id = self._shipper_get_area_id(origin=self.shipper_origin_address)
        destination_area_id = self._shipper_get_area_id(order=order)

        if not origin_area_id:
            raise UserError(_('Cannot find origin address on Shipper. Please recheck the contact\'s address or postcode.'))
        elif not destination_area_id:
            raise UserError(_('Cannot find destination address on Shipper. Please recheck the contact\'s address or postcode.'))

        rates = shipper._rate_shipment(
            self._shipper_get_package_information(order=order),
            origin_area_id,
            destination_area_id,
            order=order,
        )

        # Get the selected partner details
        selected_partner = self.shipper_3pl_partner
        selected_id = self.shipper_3pl_partner_id
        selection_dict = dict(self.fields_get(['shipper_3pl_partner'])['shipper_3pl_partner']['selection'])

        if selected_partner:
            selected_label = selection_dict[selected_partner]
            selected_name, selected_rate_type = selected_label.split(" - ", 1)
        else:
            selected_name, selected_rate_type = None, None

        filtered_rates = [
            rate for rate in rates
            if rate['rate_id'] == selected_id or (
                selected_name.lower() == rate['carrier_name'].lower() and
                selected_rate_type.lower() == rate['rate_type'].lower()
            )
        ]
        if not filtered_rates:
            raise UserError(_('No rates can be found. Please check the package dimension or Shipper configuration'))

        if filtered_rates[0]:
            if filtered_rates[0]['rate_id'] != selected_id:
                self.shipper_3pl_partner_id = filtered_rates[0]['rate_id']

            return {
                'success': True,
                'price': filtered_rates[0].get('final_price'),
                'error_message': False,
                'warning_message': False,
            }
        else:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _('Error: this delivery method is not available for this order.'),
                'warning_message': False,
            }

    def get_shipper_rate(self, order):
        """ Get the rates for the given order, according to the selected service code for this carrier.
        This method is used when getting the rate for a specific shipping.method.
        """
        shipper = self._get_shipper()
        origin_area_id = self._shipper_get_area_id(origin=self.shipper_origin_address)
        destination_area_id = self._shipper_get_area_id(order=order)

        rates = shipper._rate_shipment(
            self._shipper_get_package_information(order=order),
            origin_area_id,
            destination_area_id,
            order=order,
        )

        return rates

    # API HELPERS #
    def _shipper_get_area_id(self, order=False, origin=False):
        shipper = self._get_shipper()
        partner = order.partner_id if order and order.partner_id else origin

        res = shipper._get_area_id(partner)
        for area in res.get('data', []):
            adm_level_5 = area.get('adm_level_5', {})

            if (adm_level_5.get('postcode') == partner.zip):
                return adm_level_5.get('id')
        return False

    def _shipper_get_package_information(self, order=False, picking=False):
        original_weight_uom = self.env['product.template'].sudo()._get_weight_uom_id_from_ir_config_parameter()
        target_weight_uom = self.env.ref('uom.product_uom_kgm')

        total_weight, total_volume = 0, 0
        if order:
            for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type):
                total_weight += line.product_uom_qty * line.product_id.weight
                total_volume += line.product_uom_qty * line.product_id.volume
        elif picking:
            for move in picking.move_ids_without_package.filtered(lambda move: move.state not in ('done', 'cancel')):
                total_weight += move.quantity * move.product_id.weight
                total_volume += move.quantity * move.product_id.volume

        estimated_dimension = math.pow(total_volume, (1/3)) if total_volume > 0 else 0

        return {
            'total_weight': original_weight_uom._compute_quantity(total_weight, target_weight_uom),
            'estimated_dimension': estimated_dimension * 100,
        }

    def shipper_send_shipping(self, pickings, is_return=False):
        shipper = self._get_shipper()
        res = []
        for picking in pickings:
            if not picking.shipper_order_id:
                # TODO: for "Send to Shipper" button after the delivery is validated and in state 'done' but cancelled
                # need to add a check to trigger the create order here. The user should be allowed to do this
                # can override the send_to_shipper to call create order first
                raise UserError(_("You can only trigger a pickup after an order to Shipper is created. Please make sure to create it first."))

            order_id = picking.shipper_order_id
            if order_id:
                order_result = {
                    'exact_price': picking.shipper_order_amount,
                    'tracking_number': order_id
                }
            res.append(order_result)
            picking.carrier_tracking_ref = order_id

            pickup_response = shipper._request_pickup(order_id)
            logger.info(pickup_response)
            picking.message_post(
                body=_('Pickup request for %s was sent to Shipper with Order ID %s', picking.name, order_id)
            )
            label_response = shipper._get_shipping_label(order_id)
            label_url = label_response.get('data', {}).get('url')
            message_post = Markup(
                '{label_text} <a href="{url}" target="_blank">{link_text}</a><br>'
                "Order ID: {order_id}<br><br>"
                "It's important to note that this URL will only be accessible for a period of three days, "
                "after which it will expire. Please download the label within this timeframe to avoid any inconvenience."
            ).format(
                label_text=_("Get the shipping label:"),
                url=label_url,
                link_text=_("Here"),
                order_id=order_id
            )
            picking.message_post(body=message_post)
            picking.message_post(body=_("""Please print and stick the label on the package prior to handing it over to the
                                        courier driver as it's mandatory."""))
        return res

    def shipper_create_order(self, pickings):
        shipper = self._get_shipper()
        for picking in pickings:
            order = picking.group_id.sale_id
            origin_id = self._shipper_get_area_id(origin=self.shipper_origin_address)
            destination_id = self._shipper_get_area_id(order=picking)

            rate_id = self.shipper_3pl_partner_id or order.order_line.filtered(lambda line: line.is_delivery)[-1].name.split()[0].strip('[]')

            response = shipper._create_orders(
                self,
                picking,
                self._shipper_get_package_information(picking=picking),
                origin_id,
                destination_id,
                rate_id
            )
            order_id = response.get('data', {}).get('order_id')
            amount = response.get('data', {}).get('courier', {}).get('amount')
            if amount is not None:
                picking.shipper_order_amount = amount
            if order_id:
                picking.shipper_order_id = order_id
            picking.message_post(body=_("""Shipper order for %s was created with ID: %s.
                                         Please proceed to validate the transfer to tigger a pickup request.""",
                                        picking.name, picking.shipper_order_id))
            return response

    def shipper_cancel_shipment(self, pickings):
        shipper = self._get_shipper()
        for picking in pickings:
            if picking.shipper_order_id:
                # TODO: Add input for reason of cancellation
                shipper._cancel_order(picking.shipper_order_id, "Cancel reason")
                picking.message_post(body=_("""Shipper order for %s was cancelled""", picking.name))
                picking.shipper_order_id = False
                picking.shipper_order_amount = 0

    def _get_shipper(self):
        return Shipper(
            self.shipper_api_key,
            self.prod_environment,
            self.log_xml
        )
