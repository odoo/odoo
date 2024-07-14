# Part of Odoo. See LICENSE file for full copyright and licensing details.
import time

from odoo import fields, models, _
from odoo.exceptions import UserError, ValidationError
from .starshipit_service import Starshipit

CARRIER_SUPPORTING_RETURNS = [
    'AusPost',
    'TNT',
    'CouriersPlease',
    'Fastways',
    'StarTrack',
    'DHL',
    'NzPost',
    'PlainLabel'
]


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('starshipit', 'Starshipit'),
    ], ondelete={'starshipit': lambda records: records.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    starshipit_api_key = fields.Char(help='Starshipit API Integration key')
    starshipit_subscription_key = fields.Char(help='Starshipit API Subscription key')
    starshipit_default_package_type_id = fields.Many2one(
        'stock.package.type',
        string='Default Package Type for Starshipit',
        help='Package dimensions are required to get more accurate rates. You can define these in a package type that you set as default',
    )
    starshipit_origin_address = fields.Many2one(
        string="Origin Address",
        help="This address will be used when fetching the available services from starshipit.",
        comodel_name='res.partner',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=lambda self: self.env.company.partner_id,
    )
    starshipit_carrier_code = fields.Char(
        string='Carrier Code',
        help='The carrier on starshipit used by this carrier. The service code belongs to it.',
        export_string_translation=False,
        readonly=True,
    )
    starshipit_service_code = fields.Char(
        string='Service Code',
        help='The service that will be used for this carrier. This is set when you select a carrier from the wizard.',
        readonly=True,
    )
    starshipit_service_name = fields.Char(
        string='Service Name',
        help='The service that will be used for this carrier. This is set when you select a carrier from the wizard.',
        readonly=True,
    )

    def _compute_can_generate_return(self):
        """ Starshipit only supports returns for some carriers. """
        super()._compute_can_generate_return()
        for carrier in self:
            if carrier.delivery_type == 'starshipit':
                carrier.can_generate_return = carrier.starshipit_carrier_code in CARRIER_SUPPORTING_RETURNS

    # Shipping Carrier Methods

    def starshipit_rate_shipment(self, order):
        """ Get the rates for the given order, according to the selected service code for this carrier.
        This method is used when getting the rate for a specific shipping.method.
        """
        starshipit = self._get_starshipit()

        rates = starshipit._rate_shipment(
            self._starshipit_get_package_information(order=order)[0],
            order=order,
        )
        rate = rates['success'] and rates['rates'].get(self.starshipit_service_code)
        if rate:
            return {
                'success': True,
                'price': rate['total_price'],
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

    def starshipit_send_shipping(self, pickings, is_return=False):
        """ For a given picking, this method will execute a few API calls in order to get the order to be sent to the carrier.
        The order of actions is:
            - Create the order(s) on starshipit side. This will not send them, just register them and return the id(s)
            - Get the labels for each picking, one at a time. This will return the tracking number(s) and url(s).
                - The labels are attached to the picking as ir.attachment
            - If return_label_on_delivery is set, generate the return label(s) for each picking too.
            - Get the delivery order information from starshipit to fetch the final rate, and whether the order was manifested or not.
            - Finally either manifest (send) the order(s) or archive them in test mode.
              If sent, the manifest report is added to the picking as ir.attachment.
        """
        starshipit = self._get_starshipit()
        unshipped_orders = starshipit._create_orders(self, pickings, is_return)['orders']
        res = []

        for picking in pickings:
            starshipit_order_number = starshipit._get_starshipit_order_number(picking)
            # We cant use the api that prints labels for multiple order at once because this endpoint doesn't return the tracking information.
            order = unshipped_orders.get(starshipit_order_number)
            order_id = order['order_id']
            picking.starshipit_parcel_reference = order_id

            # The 'total_shipping_price' is required in order to get the exact_price.
            # It seems that this is computed by starshipit asynchronously and that we could need to wait a bit to get it.
            # We cannot delete the order once it has been labelled, so we need to ensure that this exists before moving forward.
            # To that end, we will loop and try up to 3 times before labelling.
            total_shipping_price = None
            tries = 0

            while not total_shipping_price and tries < 3:
                tries += 1
                order_data = starshipit._get_order_details(order_id)
                total_shipping_price = order_data['order'].get('total_shipping_price', None)
                if total_shipping_price:
                    break
                time.sleep(1)

            # If we still couldn't get it after three tries (unlikely), we will ask the user to try again.
            if not total_shipping_price:
                error_messages = [_('There was an issue when creating the order, please try again')]
                try:
                    starshipit._delete_order(order_id)
                except UserError:
                    error_messages.append(_(' after deleting the order on Starshipit'))
                finally:
                    raise UserError(''.join(error_messages))

            order_result = {
                'exact_price': total_shipping_price,
            }

            label_data = self._create_label_for_order(order_id)

            tracking_number = ', '.join(tracking_number for tracking_number in label_data['tracking_numbers'] if tracking_number is not None)
            picking.carrier_tracking_ref = tracking_number
            try:
                # generate return if config is set
                if self.return_label_on_delivery:
                    self.get_return_label(picking)
            except UserError:
                # if the return fails need to log that they failed and continue
                picking.message_post(body=_('The return label creation failed.'))

            # Get the exact price for the shipping.
            attachment_data = []
            # Attach the labels we got to the picking
            for label in label_data['labels']:
                attachment_data.append({
                    'name': f'{self._get_delivery_label_prefix()}-{picking.name.replace("/", "_").lower()}.pdf',
                    'datas': label,
                    'type': 'binary',
                    'res_model': picking._name,
                    'res_id': picking.id,
                })
            attachment_ids = self.env['ir.attachment'].create(attachment_data)
            # Before continuing, get the order info and check if it was automatically manifested.
            order_data = starshipit._get_order_details(order_id)
            manifested = order_data['order']['manifested']
            # Get the final rate from the order information.
            order_result['tracking_number'] = tracking_number
            res.append(order_result)
            if attachment_ids:
                picking.message_post(body=_('Labels were generated for the order %s', picking.name), attachment_ids=attachment_ids.ids)
            # In production, we can manifest the order, and it will be sent to the carrier.
            if self.prod_environment:
                if not manifested:
                    result = starshipit._manifest_orders([picking.starshipit_parcel_reference])
                    attachment_id = self.env['ir.attachment'].create({
                        'name': f'{self._get_delivery_doc_prefix()}-manifest-report-{picking.name.replace("/", "_").lower()}.pdf',
                        'datas': result['pdf'],
                        'type': 'binary',
                        'res_model': picking._name,
                        'res_id': picking.id,
                    })
                    picking.message_post(body=_('Order %s was sent to the carrier.', picking.name), attachment_ids=attachment_id.ids)
                else:
                    picking.message_post(body=_('Order %s was already sent to the carrier during label creation.\n'
                                                'Manifest number: %s', picking.name, order_data['order']['manifest_number']))
            # In test mode, we will archive the order instead to avoid any fees related to the end carrier.
            else:
                if manifested:
                    picking.message_post(body=_('Order %s was sent to the carrier during label creation.'
                                                'As you are in a test environment, please make sure to cancel the order with your carrier directly.\n'
                                                'Manifest number: %s', picking.name, order_data['order']['manifest_number']))
                self._starshipit_cancel_shipment(picking)
                picking.message_post(body=_('Order %s was archived.', picking.name))
        return res

    def starshipit_get_tracking_link(self, picking):
        """ Get the tracking link for the given picking.
        """
        starshipit = self._get_starshipit()
        starshipit_order_number = starshipit._get_starshipit_order_number(picking)
        result = starshipit._get_tracking_link(starshipit_order_number)
        return result.get('results', {}).get('tracking_url', False)

    def _starshipit_cancel_shipment(self, pickings):
        """ Archive the shipment on starshipit side.
        Note that this will not do anything with the carrier and the user is expected to handle that himself.
        This is done instead of trying to cancel as we always label right away and once labelled, we cannot cancel anymore.
        """
        starshipit = self._get_starshipit()
        for picking in pickings:
            starshipit._archive_order(picking.starshipit_parcel_reference)

    def starshipit_action_load_shipping_carriers(self):
        """ The deliveryservices endpoint is used to get the list of available carriers.

        As we need to give an address, we will use the company one.
        """
        self.ensure_one()
        if self.delivery_type != 'starshipit':
            raise ValidationError(_('This action requires a Starshipit carrier.'))
        starshipit = self._get_starshipit()
        available_services = starshipit._get_delivery_services(self.starshipit_origin_address)
        if not available_services.get('services'):
            raise UserError(_("There are no shipping services available, please verify the shipping address or activate suitable carriers in your starshipit account."))

        return {
            'name': _("Choose Starshipit Shipping Service"),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'starshipit.shipping.wizard',
            'target': 'new',
            'context': {
                'default_carrier_id': self.id,
                'default_available_services': available_services['services'],
                'default_selected_service_code': self.starshipit_service_code,
            },
        }

    def starshipit_get_return_label(self, picking, tracking_number=None, origin_date=None):
        """ Generate a return order/label for the given picking.
        The flow is very similar  to the send shipping flow, with a few differences.
        """
        starshipit = self._get_starshipit()
        if picking.starshipit_parcel_reference:
            order = starshipit._clone_order(picking.starshipit_parcel_reference)['order']
        else:
            starshipit_order_number = starshipit._get_starshipit_order_number(picking)
            order = starshipit._create_orders(self, picking, True)['orders'].get(starshipit_order_number)

        order_id = order['order_id']
        label_data = self._create_label_for_order(order_id)

        # if picking is not a return means we are pre-generating the return label on delivery
        # thus we save the returned parcel id in a separate field
        if picking.is_return_picking:
            picking.starshipit_parcel_reference = order['order_id']
        else:
            picking.starshipit_return_parcel_reference = order['order_id']

        attachment_data = []
        # Attach the labels we got to the picking.
        for label in label_data['labels']:
            attachment_data.append({
                'name': f'{self.get_return_label_prefix()}-{picking.name.replace("/", "_").lower()}.pdf',
                'datas': label,
                'type': 'binary',
                'res_model': picking._name,
                'res_id': picking.id,
            })
        attachment_ids = self.env['ir.attachment'].create(attachment_data)
        # Before continuing, get the order info and check if it was automatically manifested.
        order_data = starshipit._get_order_details(order_id)
        manifested = order_data['order']['manifested']
        if attachment_ids:
            picking.message_post(body=_('Return labels were generated for the order %s', picking.name), attachment_ids=attachment_ids.ids)
        # In production, we can manifest the order, and it will be sent to the carrier.
        if self.prod_environment:
            if not manifested:
                result = starshipit._manifest_orders([picking.starshipit_parcel_reference])
                attachment_id = self.env['ir.attachment'].create({
                    'name': f'{self._get_delivery_doc_prefix()}-{picking.name.replace("/", "_").lower()}.pdf',
                    'datas': result['pdf'],
                    'type': 'binary',
                    'res_model': picking._name,
                    'res_id': picking.id,
                })
                picking.message_post(body=_('Return order %s was sent to the carrier.', picking.name), attachment_ids=attachment_id.ids)
            else:
                picking.message_post(body=_('Return order %s was already sent to the carrier during label creation.\n'
                                            'Manifest number: %s', picking.name, order_data['order']['manifest_number']))
        # In test mode, we will archive the order instead to avoid any fees related to the end carrier.
        else:
            if manifested:
                picking.message_post(body=_('Return order %s was sent to the carrier during label creation.'
                                            'As you are in a test environment, please make sure to cancel the order with your carrier directly.\n'
                                            'Manifest number: %s', picking.name, order_data['order']['manifest_number']))
            self._starshipit_cancel_shipment(picking)
            picking.message_post(body=_('Return order %s was archived.', picking.name))

    def _create_label_for_order(self, order_id):
        starshipit = self._get_starshipit()

        label_creation_failed = False
        label_data = False
        label_creation_errors = []
        try:
            label_data = starshipit._create_label(order_id)
        except UserError as e:
            label_creation_failed = True
            label_creation_errors.append(_('The shipping label creation failed with the following error:\n%(error)s',
                                           error=e))

        if label_creation_failed:
            try:
                starshipit._delete_order(order_id)
            except UserError:
                label_creation_errors.append(_('Please delete the order on Starshipit then try again.'))
            finally:
                raise UserError('\n'.join(label_creation_errors))
        return label_data

    # API HELPERS #

    def _starshipit_get_package_information(self, order=False, picking=False):
        """ Given an order or a picking, this method returns the formatted package information to send to Starshipit.
        It also returns the list of items in the package in case the endpoint needs it.
        The method also makes sure that the UOM used in the package information matches the one used by Starshipit. (Kgm and meter)
        """
        packages = []
        package_items = []
        original_weight_uom = self.env['product.template'].sudo()._get_weight_uom_id_from_ir_config_parameter()
        target_weight_uom = self.env.ref('uom.product_uom_kgm')
        original_length_uom = self.env['product.template'].sudo()._get_length_uom_id_from_ir_config_parameter()
        target_length_uom = self.env.ref('uom.product_uom_meter')
        if picking:
            # Will get the precise package information, with the packages set on the picking if any.
            # When used to rate the order, this will be accurate.
            delivery_packages = self._get_packages_from_picking(picking, self.starshipit_default_package_type_id)
        elif order:
            # Will get the package information based on the default package on the carrier.
            # When used to rate the order, this could be inaccurate.
            delivery_packages = self._get_packages_from_order(order, self.starshipit_default_package_type_id)
        else:
            return [], []

        for package in delivery_packages:
            for commodity in package.commodities:
                hs_code = commodity.product_id.hs_code or ''
                for ch in [' ', '.']:
                    if ch in hs_code:
                        hs_code = hs_code.replace(ch, '')
                package_items.append({
                    'description': commodity.product_id.name,
                    'sku': commodity.product_id.barcode or '',
                    'tariff_code': hs_code,
                    'country_of_origin': commodity.country_of_origin or '',
                    'quantity': commodity.qty,
                    'weight': original_weight_uom._compute_quantity(commodity.product_id.weight, target_weight_uom),
                    'value': commodity.monetary_value,
                })
            package_val = {
                'weight': original_weight_uom._compute_quantity(package.weight, target_weight_uom),
                'height': original_length_uom._compute_quantity(package.dimension.get('height', 0.0), target_length_uom),
                'width': original_length_uom._compute_quantity(package.dimension.get('width', 0.0), target_length_uom),
                'length': original_length_uom._compute_quantity(package.dimension.get('length', 0.0), target_length_uom),
            }
            packages.append(package_val)

        return packages, package_items

    def get_return_label(self, pickings, tracking_number=None, origin_date=None):
        """ Log a warning if the user tries to generate a return label for a carrier that doesn't support it. """
        self.ensure_one()
        if not self.can_generate_return and self.delivery_type == 'starshipit':
            for picking in pickings:
                picking.message_post(body=_('Starshipit cannot generate returns for the carrier %s. '
                                            'Please handle this return with the carrier directly.', self.starshipit_carrier_code))
        return super().get_return_label(pickings, tracking_number=tracking_number, origin_date=origin_date)

    def _get_starshipit(self):
        return Starshipit(
            self.starshipit_api_key,
            self.starshipit_subscription_key,
            self.log_xml
        )
