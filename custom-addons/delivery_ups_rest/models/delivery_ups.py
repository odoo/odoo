# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import pdf

from .ups_request import UPSRequest


class ProviderUPS(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('ups_rest', "UPS")
    ], ondelete={'ups_rest': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    ups_shipper_number = fields.Char(string='UPS Account Number', groups="base.group_system")
    ups_client_id = fields.Char(string='UPS Client ID', groups="base.group_system")
    ups_client_secret = fields.Char(string='UPS Client Secret', groups="base.group_system")
    ups_access_token = fields.Char(string='UPS Access Token', groups="base.group_system")
    ups_default_packaging_id = fields.Many2one('stock.package.type', string='UPS Package Type')
    ups_default_service_type = fields.Selection([
        ('03', 'UPS Ground'),
        ('11', 'UPS Standard'),
        ('01', 'UPS Next Day'),
        ('14', 'UPS Next Day AM'),
        ('13', 'UPS Next Day Air Saver'),
        ('02', 'UPS 2nd Day'),
        ('59', 'UPS 2nd Day AM'),
        ('12', 'UPS 3-day Select'),
        ('65', 'UPS Saver'),
        ('07', 'UPS Worldwide Express'),
        ('08', 'UPS Worldwide Expedited'),
        ('54', 'UPS Worldwide Express Plus'),
        ('96', 'UPS Worldwide Express Freight')
    ], string="UPS Service Type", default='03')
    ups_package_weight_unit = fields.Selection([('LBS', 'Pounds'), ('KGS', 'Kilograms')], default='LBS')
    ups_package_dimension_unit = fields.Selection([('IN', 'Inches'), ('CM', 'Centimeters')], string="Package Size Unit", default='IN')
    ups_label_file_type = fields.Selection([('GIF', 'PDF'),
                                            ('ZPL', 'ZPL'),
                                            ('EPL', 'EPL'),
                                            ('SPL', 'SPL')],
                                           string="UPS Label File Type", default='GIF')
    ups_bill_my_account = fields.Boolean(string='Bill My Account',
                                         help="If checked, ecommerce users will be prompted their UPS account number\n"
                                              "and delivery fees will be charged on it.")
    ups_duty_payment = fields.Selection([('SENDER', 'Sender'), ('RECIPIENT', 'Recipient')], required=True, default="RECIPIENT")
    ups_cod = fields.Boolean(string='Collect on Delivery',
                             help='This value added service enables UPS to collect the payment of the shipment from your customer.')
    ups_saturday_delivery = fields.Boolean(string='UPS Saturday Delivery',
                                           help='This value added service will allow you to ship the package on saturday also.')
    ups_cod_funds_code = fields.Selection(selection=[
        ('0', "Check, Cashier's Check or MoneyOrder"),
        ('8', "Cashier's Check or MoneyOrder"),
        ], string='COD Funding Option', default='0')

    def _compute_can_generate_return(self):
        super()._compute_can_generate_return()
        for carrier in self.filtered(lambda c: c.delivery_type == 'ups_rest'):
            carrier.can_generate_return = True

    def _compute_supports_shipping_insurance(self):
        super(ProviderUPS, self)._compute_supports_shipping_insurance()
        for carrier in self:
            if carrier.delivery_type == 'ups_rest':
                carrier.supports_shipping_insurance = True

    @api.onchange('ups_default_service_type')
    def on_change_service_type(self):
        self.ups_cod = False
        self.ups_saturday_delivery = False

    def ups_rest_rate_shipment(self, order):
        ups = UPSRequest(self)
        packages = self._get_packages_from_order(order, self.ups_default_packaging_id)

        if self.ups_cod:
            cod_info = {
                'currency': order.partner_id.country_id.currency_id.name,
                'monetary_value': order.amount_total,
                'funds_code': self.ups_cod_funds_code,
            }
        else:
            cod_info = None

        check_value = ups._check_required_value(order=order)
        if check_value:
            return {'success': False,
                    'price': 0.0,
                    'error_message': check_value,
                    'warning_message': False}

        total_qty = sum([line.product_uom_qty for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type)])

        result = ups._get_shipping_price(order.company_id.partner_id, order.warehouse_id.partner_id,
                                         order.partner_shipping_id, total_qty, packages, self, cod_info=cod_info)

        if result.get('error_message'):
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error:\n%s', result['error_message']),
                    'warning_message': False}

        if order.currency_id.name == result['currency_code']:
            price = float(result['price'])
        else:
            quote_currency = self.env['res.currency'].search([('name', '=', result['currency_code'])], limit=1)
            price = quote_currency._convert(
                float(result['price']), order.currency_id, order.company_id, order.date_order or fields.Date.today())

        if self.ups_bill_my_account and order.partner_ups_carrier_account:
            # Don't show delivery amount, if ups bill my account option is true
            price = 0.0

        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': result.get('alert_message', False)}

    def _prepare_shipping_data(self, picking):
        packages = self._get_packages_from_picking(picking, self.ups_default_packaging_id)

        terms_of_shipment = picking.company_id.incoterm_id
        if picking.sale_id and picking.sale_id.incoterm:
            terms_of_shipment = picking.sale_id.incoterm

        shipment_info = {
            'require_invoice': picking._should_generate_commercial_invoice(),
            'invoice_date': fields.Date.today().strftime('%Y%m%d'),
            'description': picking.origin or picking.name,
            'total_qty': sum(sml.quantity for sml in picking.move_line_ids),
            'ilt_monetary_value': '%d' % sum(sml.sale_price for sml in picking.move_line_ids),
            'itl_currency_code': self.env.company.currency_id.name,
            'phone': picking.partner_id.mobile or picking.partner_id.phone or picking.sale_id.partner_id.mobile or picking.sale_id.partner_id.phone,
            'terms_of_shipment': terms_of_shipment.code if terms_of_shipment else None,
            'purchase_order_number': picking.sale_id.name if picking.sale_id else None,
        }
        if picking.sale_id and picking.sale_id.carrier_id != picking.carrier_id:
            ups_service_type = picking.carrier_id.ups_default_service_type or self.ups_default_service_type
        else:
            ups_service_type = self.ups_default_service_type
        ups_carrier_account = False
        if self.ups_bill_my_account:
            ups_carrier_account = picking.partner_id.with_company(picking.company_id).property_ups_carrier_account

        if picking.carrier_id.ups_cod:
            cod_info = {
                'currency': picking.partner_id.country_id.currency_id.name,
                'monetary_value': picking.sale_id.amount_total,
                'funds_code': self.ups_cod_funds_code,
            }
        else:
            cod_info = None
        return packages, shipment_info, ups_service_type, ups_carrier_account, cod_info

    def ups_rest_send_shipping(self, pickings):
        res = []
        ups = UPSRequest(self)
        for picking in pickings:
            packages, shipment_info, ups_service_type, ups_carrier_account, cod_info = self._prepare_shipping_data(picking)

            check_value = ups._check_required_value(picking=picking)
            if check_value:
                raise UserError(check_value)

            result = ups._send_shipping(
                shipment_info=shipment_info, packages=packages, carrier=self, shipper=picking.company_id.partner_id, ship_from=picking.picking_type_id.warehouse_id.partner_id,
                ship_to=picking.partner_id, service_type=ups_service_type, duty_payment=picking.carrier_id.ups_duty_payment,
                saturday_delivery=picking.carrier_id.ups_saturday_delivery, cod_info=cod_info,
                label_file_type=self.ups_label_file_type, ups_carrier_account=ups_carrier_account)

            order = picking.sale_id
            company = order.company_id or picking.company_id or self.env.company
            currency_order = picking.sale_id.currency_id
            if not currency_order:
                currency_order = picking.company_id.currency_id

            if currency_order.name == result['currency_code']:
                price = float(result['price'])
            else:
                quote_currency = self.env['res.currency'].search([('name', '=', result['currency_code'])], limit=1)
                price = quote_currency._convert(
                    float(result['price']), currency_order, company, order.date_order or fields.Date.today())

            package_labels = result.get('label_binary_data', [])

            carrier_tracking_ref = "+".join([pl[0] for pl in package_labels])
            logmessage = _("Shipment created into UPS<br/>"
                           "<b>Tracking Numbers:</b> %s<br/>"
                           "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([p.name for p in packages if p.name]))
            if self.ups_label_file_type != 'GIF':
                attachments = [('LabelUPS-%s.%s' % (pl[0], self.ups_label_file_type), pl[1]) for pl in package_labels]
            else:
                attachments = [('LabelUPS.pdf', pdf.merge_pdf([pl[1] for pl in package_labels]))]
            if result.get('invoice_binary_data'):
                attachments.append(('UPSCommercialInvoice.pdf', result['invoice_binary_data']))
            picking.message_post(body=logmessage, attachments=attachments)
            shipping_data = {
                'exact_price': price,
                'tracking_number': carrier_tracking_ref}
            res = res + [shipping_data]
            if self.return_label_on_delivery:
                try:
                    self.ups_rest_get_return_label(picking)
                except (UserError, ValidationError) as err:
                    try:
                        ups._cancel_shipping(result['tracking_ref'])
                    except ValidationError:
                        pass
                    raise UserError(err)
        return res

    def ups_rest_get_return_label(self, picking, tracking_number=None, origin_date=None):
        res = []
        ups = UPSRequest(self)
        packages, shipment_info, ups_service_type, ups_carrier_account, cod_info = self._prepare_shipping_data(picking)

        check_value = ups._check_required_value(picking=picking, is_return=True)
        if check_value:
            raise UserError(check_value)

        result = ups._send_shipping(
            shipment_info=shipment_info, packages=packages, carrier=self, shipper=picking.partner_id, ship_from=picking.partner_id,
            ship_to=picking.picking_type_id.warehouse_id.partner_id, service_type=ups_service_type, duty_payment='RECIPIENT', saturday_delivery=picking.carrier_id.ups_saturday_delivery,
            cod_info=cod_info, label_file_type=self.ups_label_file_type, ups_carrier_account=ups_carrier_account, is_return=True)

        order = picking.sale_id
        company = order.company_id or picking.company_id or self.env.company
        currency_order = picking.sale_id.currency_id
        if not currency_order:
            currency_order = picking.company_id.currency_id

        if currency_order.name == result['currency_code']:
            price = float(result['price'])
        else:
            quote_currency = self.env['res.currency'].search([('name', '=', result['currency_code'])], limit=1)
            price = quote_currency._convert(
                float(result['price']), currency_order, company, order.date_order or fields.Date.today())

        package_labels = []
        for track_number, label_binary_data in result.get('label_binary_data'):
            package_labels = package_labels + [(track_number, label_binary_data)]

        carrier_tracking_ref = "+".join([pl[0] for pl in package_labels])
        logmessage = _("Return label generated<br/>"
                        "<b>Tracking Numbers:</b> %s<br/>"
                        "<b>Packages:</b> %s") % (carrier_tracking_ref, ','.join([p.name for p in packages if p.name]))
        if self.ups_label_file_type != 'GIF':
            attachments = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), pl[0], index, self.ups_label_file_type), pl[1]) for index, pl in enumerate(package_labels)]
        else:
            attachments = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), package_labels[0][0], 1, 'pdf'), pdf.merge_pdf([pl[1] for pl in package_labels]))]
        picking.message_post(body=logmessage, attachments=attachments)
        shipping_data = {
            'exact_price': price,
            'tracking_number': carrier_tracking_ref}
        res = res + [shipping_data]
        return res

    def ups_rest_get_tracking_link(self, picking):
        return 'http://wwwapps.ups.com/WebTracking/track?track=yes&trackNums=%s' % picking.carrier_tracking_ref

    def ups_rest_cancel_shipment(self, picking):
        ups = UPSRequest(self)
        ups._cancel_shipping(picking.carrier_tracking_ref)
        picking.message_post(body=_(u'Shipment #%s has been cancelled', picking.carrier_tracking_ref))
        picking.write({'carrier_tracking_ref': '',
                        'carrier_price': 0.0})

    def _ups_get_default_custom_package_code(self):
        return '02'

    def _ups_convert_weight(self, weight, unit='KGS'):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if unit == 'KGS':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)
        elif unit == 'LBS':
            return weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'), round=False)
        else:
            raise ValueError
