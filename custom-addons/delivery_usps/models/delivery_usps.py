# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import math
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .usps_request import USPSRequest



class ProviderUSPS(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('usps', "USPS")
    ], ondelete={'usps': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    # Fields required to configure
    usps_username = fields.Char(string='USPS User ID', groups="base.group_system")
    usps_account_validated = fields.Boolean(string="Account Validated", help="Check this box if your account is validated by USPS")
    usps_delivery_nature = fields.Selection([('domestic', 'Domestic'),
                                             ('international', 'International')],
                                            string="Delivery Nature", default='domestic', required=True)
    usps_size_container = fields.Selection([('LARGE', 'Large'),
                                            ('REGULAR', 'Regular')],
                                           default='REGULAR', store=True, compute='_compute_size_container')

    @api.depends('usps_container')
    def _compute_size_container(self):
        for rec in self:
            if rec.usps_container == 'VARIABLE':
                rec.usps_size_container = 'REGULAR'
            else:
                rec.usps_size_container = 'LARGE'

    usps_label_file_type = fields.Selection([('PDF', 'PDF'),
                                             ('TIF', 'TIF')],
                                            string="USPS Label File Type", default='PDF')
    usps_service = fields.Selection([('First Class', 'First Class'),
                                     ('Priority', 'Priority'),
                                     ('Express', 'Express')],
                                    required=True, string="USPS Service", default="Express")
    usps_first_class_mail_type = fields.Selection([('LETTER', 'Letter'),
                                                   ('FLAT', 'Flat'),
                                                   ('PARCEL', 'Parcel'),
                                                   ('POSTCARD', 'Postcard'),
                                                   ('PACKAGE SERVICE', 'Package Service')],
                                                  string="USPS First Class Mail Type", default="LETTER")
    usps_container = fields.Selection([('VARIABLE', 'Regular < 12 inch'),
                                       ('RECTANGULAR', 'Rectangular'),
                                       ('NONRECTANGULAR', 'Non-rectangular')],
                                      required=True, default='VARIABLE', string="Type of container")
    usps_domestic_regular_container = fields.Selection([('Flat Rate Envelope', 'Flat Rate Envelope'),
                                                        ('Sm Flat Rate Envelope', 'Small Flat Rate Envelope'),
                                                        ('Legal Flat Rate Envelope', 'Legal Flat Rate Envelope'),
                                                        ('Padded Flat Rate Envelope', 'Padded Flat Rate Envelope'),
                                                        ('Flat Rate Box', 'Flat Rate Box'),
                                                        ('Sm Flat Rate Box', 'Small Flat Rate Box'),
                                                        ('Lg Flat Rate Box', 'Large Flat Rate Box'),
                                                        ('Md Flat Rate Box', 'Medium Flat Rate Box')],
                                                       string="Type of USPS domestic regular container", default="Lg Flat Rate Box")

    # For international shipping
    usps_international_regular_container = fields.Selection([('FLATRATEENV', 'Flat Rate Envelope'),
                                                             ('LEGALFLATRATEENV', 'Legal Flat Rate Envelope'),
                                                             ('PADDEDFLATRATEENV', 'Padded Flat Rate Envelope'),
                                                             ('FLATRATEBOX', 'Flat Rate Box')],
                                                            string="Type of USPS International regular container", default="FLATRATEBOX")
    usps_mail_type = fields.Selection([('Package', 'Package'),
                                       ('Letter', 'Letter'),
                                       ('FlatRate', 'Flat Rate'),
                                       ('FlatRateBox', 'Flat Rate Box'),
                                       ('LargeEnvelope', 'Large Envelope')],
                                      default="FlatRateBox", string="USPS Mail Type")
    usps_content_type = fields.Selection([('SAMPLE', 'Sample'),
                                          ('GIFT', 'Gift'),
                                          ('DOCUMENTS', 'Documents'),
                                          ('RETURN', 'Return'),
                                          ('MERCHANDISE', 'Merchandise')],
                                         default='MERCHANDISE', string="Content Type")
    usps_custom_container_width = fields.Float(string='Package Width')
    usps_custom_container_length = fields.Float(string='Package Length')
    usps_custom_container_height = fields.Float(string='Package Height')
    usps_custom_container_girth = fields.Float(string='Package Girth')
    usps_intl_non_delivery_option = fields.Selection([('RETURN', 'Return'),
                                                      ('REDIRECT', 'Redirect'),
                                                      ('ABANDON', 'Abandon')],
                                                     default="ABANDON", string="Non delivery option")
    usps_redirect_partner_id = fields.Many2one('res.partner', string="Redirect Partner")
    usps_machinable = fields.Boolean(string="Machinable", help="Please check on USPS website to ensure that your package is machinable.")

    @api.depends('usps_delivery_nature')
    def _compute_can_generate_return(self):
        super(ProviderUSPS, self)._compute_can_generate_return()
        for carrier in self:
            if carrier.delivery_type == 'usps':
                if carrier.usps_delivery_nature == 'international':
                    carrier.can_generate_return = False
                else:
                    carrier.can_generate_return = True

    def usps_rate_shipment(self, order):
        srm = USPSRequest(self.prod_environment, self.log_xml)

        check_result = srm.check_required_value(order.partner_shipping_id, self.usps_delivery_nature, order.warehouse_id.partner_id, order=order)
        if check_result:
            return {'success': False,
                    'price': 0.0,
                    'error_message': check_result,
                    'warning_message': False}

        quotes = srm.usps_rate_request(order, self)

        if quotes.get('error_message'):
            return {'success': False,
                    'price': 0.0,
                    'error_message': _('Error:\n%s', quotes['error_message']),
                    'warning_message': False}

        # USPS always returns prices in USD
        if order.currency_id.name == 'USD':
            price = quotes['price']
        else:
            quote_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
            price = quote_currency._convert(
              quotes['price'], order.currency_id, order.company_id, order.date_order or fields.Date.today())

        return {'success': True,
                'price': price,
                'error_message': False,
                'warning_message': False}

    def usps_send_shipping(self, pickings):
        res = []
        srm = USPSRequest(self.prod_environment, self.log_xml)
        for picking in pickings:
            check_result = srm.check_required_value(picking.partner_id, self.usps_delivery_nature, picking.picking_type_id.warehouse_id.partner_id, picking=picking)
            if check_result:
                raise UserError(check_result)

            booking = srm.usps_request(picking, self.usps_delivery_nature, self.usps_service, is_return=False)

            if booking.get('error_message'):
                raise UserError(booking['error_message'])

            order = picking.sale_id
            company = order.company_id or picking.company_id or self.env.company
            currency_order = picking.sale_id.currency_id
            if not currency_order:
                currency_order = picking.company_id.currency_id

            # USPS always returns prices in USD
            if currency_order.name == "USD":
                price = booking['price']
            else:
                quote_currency = self.env['res.currency'].search([('name', '=', "USD")], limit=1)
                price = quote_currency._convert(
                  booking['price'], currency_order, company, order.date_order or fields.Date.today())

            carrier_tracking_ref = booking['tracking_number']

            logmessage = Markup(_("Shipment created into USPS <br/> <b>Tracking Number: </b>%s")) % carrier_tracking_ref
            usps_labels = [('%s-%s.%s' % (self._get_delivery_label_prefix(), carrier_tracking_ref, self.usps_label_file_type), booking['label'])]
            if picking.sale_id:
                for pick in picking.sale_id.picking_ids:
                    pick.message_post(body=logmessage, attachments=usps_labels)
            else:
                picking.message_post(body=logmessage, attachments=usps_labels)

            shipping_data = {'exact_price': price,
                             'tracking_number': carrier_tracking_ref}
            res = res + [shipping_data]
            if self.return_label_on_delivery:
                self.get_return_label(picking)
        return res

    def usps_get_return_label(self, picking, tracking_number=None, origin_date=None):
        res = []
        srm = USPSRequest(self.prod_environment, self.log_xml)
        check_result = srm.check_required_value(picking.partner_id, self.usps_delivery_nature, picking.picking_type_id.warehouse_id.partner_id, picking=picking)
        if check_result:
            raise UserError(check_result)

        booking = srm.usps_request(picking, self.usps_delivery_nature, self.usps_service, is_return=True)

        if booking.get('error_message'):
            raise UserError(booking['error_message'])

        carrier_tracking_ref = booking['tracking_number']
        logmessage = _("Shipment created into USPS") + Markup("<br/> <b>") + \
                     _("Tracking Number:") + Markup("</b> ") + carrier_tracking_ref
        picking.message_post(body=logmessage, attachments=[('%s-%s-%s.%s' % (self.get_return_label_prefix(), carrier_tracking_ref, 1, self.usps_label_file_type), booking['label'])])


    def usps_get_tracking_link(self, picking):
        return 'https://tools.usps.com/go/TrackConfirmAction_input?qtc_tLabels1=%s' % picking.carrier_tracking_ref

    def usps_cancel_shipment(self, picking):

        srm = USPSRequest(self.prod_environment, self.log_xml)

        result = srm.cancel_shipment(picking, self.usps_account_validated)

        if result['error_found']:
            raise UserError(result['error_message'])
        else:
            picking.message_post(body=_(u'Shipment #%s has been cancelled', picking.carrier_tracking_ref))
            picking.write({'carrier_tracking_ref': '',
                           'carrier_price': 0.0})

    def _usps_convert_weight(self, weight):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        weight_in_pounds = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'))
        pounds = int(math.floor(weight_in_pounds))
        ounces = round((weight_in_pounds - pounds) * 16, 3)
        # ounces should be at least 1 for the api request not to fail.
        if pounds == 0 and int(ounces) == 0:
            ounces = 1
        return {'pound': pounds, 'ounce': ounces}
