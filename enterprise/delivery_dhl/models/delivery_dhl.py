# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .dhl_request import DHLProvider
from markupsafe import Markup
from odoo.tools.zeep.helpers import serialize_object

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_repr
from odoo.tools.safe_eval import const_eval


class Providerdhl(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('dhl', "DHL (Legacy)")
    ], ondelete={'dhl': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})

    dhl_SiteID = fields.Char(string="DHL SiteID", groups="base.group_system")
    dhl_password = fields.Char(string="DHL Password", groups="base.group_system")
    dhl_account_number = fields.Char(string="DHL Account Number", groups="base.group_system")
    dhl_package_dimension_unit = fields.Selection([('I', 'Inches'),
                                                   ('C', 'Centimeters')],
                                                  default='C',
                                                  string='Package Dimension Unit')
    dhl_package_weight_unit = fields.Selection([('L', 'Pounds'),
                                                ('K', 'Kilograms')],
                                               default='K',
                                               string="Package Weight Unit")
    dhl_default_package_type_id = fields.Many2one('stock.package.type', string='DHL Legacy Package Type')
    dhl_region_code = fields.Selection([('AP', 'Asia Pacific'),
                                        ('AM', 'America'),
                                        ('EU', 'Europe')],
                                       default='AM',
                                       string='Region')
    # Nowadays hidden, by default it's the D, couldn't find any documentation on other services
    dhl_product_code = fields.Selection([('0', '0 - Logistics Services'),
                                         ('1', '1 - Domestic Express 12:00'),
                                         ('2', '2 - B2C'),
                                         ('3', '3 - B2C'),
                                         ('4', '4 - Jetline'),
                                         ('5', '5 - Sprintline'),
                                         ('6', '6 - Secureline'),
                                         ('7', '7 - Express Easy'),
                                         ('8', '8 - Express Easy'),
                                         ('9', '9 - Europack'),
                                         ('A', 'A - Auto Reversals'),
                                         ('B', 'B - Break Bulk Express'),
                                         ('C', 'C - Medical Express'),
                                         ('D', 'D - Express Worldwide'),
                                         ('E', 'E - Express 9:00'),
                                         ('F', 'F - Freight Worldwide'),
                                         ('G', 'G - Domestic Economy Select'),
                                         ('H', 'H - Economy Select'),
                                         ('I', 'I - Break Bulk Economy'),
                                         ('J', 'J - Jumbo Box'),
                                         ('K', 'K - Express 9:00'),
                                         ('L', 'L - Express 10:30'),
                                         ('M', 'M - Express 10:30'),
                                         ('N', 'N - Domestic Express'),
                                         ('O', 'O - DOM Express 10:30'),
                                         ('P', 'P - Express Worldwide'),
                                         ('Q', 'Q - Medical Express'),
                                         ('R', 'R - GlobalMail Business'),
                                         ('S', 'S - Same Day'),
                                         ('T', 'T - Express 12:00'),
                                         ('U', 'U - Express Worldwide'),
                                         ('V', 'V - Europack'),
                                         ('W', 'W - Economy Select'),
                                         ('X', 'X - Express Envelope'),
                                         ('Y', 'Y - Express 12:00'),
                                         ('Z', 'Z - Destination Charges'),
                                         ],
                                        default='D',
                                        string='DHL Product')
    dhl_dutiable = fields.Boolean(string="Dutiable Material", help="Check this if your package is dutiable.")
    dhl_duty_payment = fields.Selection([('S', 'Sender'), ('R', 'Recipient')], required=True, default="S")
    dhl_label_image_format = fields.Selection([
        ('EPL2', 'EPL2'),
        ('PDF', 'PDF'),
        ('ZPL2', 'ZPL2'),
    ], string="Label Image Format", default='PDF')
    dhl_label_template = fields.Selection([
        ('8X4_A4_PDF', '8X4_A4_PDF'),
        ('8X4_thermal', '8X4_thermal'),
        ('8X4_A4_TC_PDF', '8X4_A4_TC_PDF'),
        ('6X4_thermal', '6X4_thermal'),
        ('6X4_A4_PDF', '6X4_A4_PDF'),
        ('8X4_CI_PDF', '8X4_CI_PDF'),
        ('8X4_CI_thermal', '8X4_CI_thermal'),
        ('8X4_RU_A4_PDF', '8X4_RU_A4_PDF'),
        ('6X4_PDF', '6X4_PDF'),
        ('8X4_PDF', '8X4_PDF')
    ], string="Label Template", default='8X4_A4_PDF')
    dhl_custom_data_request = fields.Text(
        'Custom data for DHL requests,',
        help="""The custom data in DHL is organized like the inside of a json file.
        There are 3 possible keys: 'rate', 'ship', 'return', to which you can add your custom data.
        More info on https://xmlportal.dhl.com/"""
    )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_commercial_invoice_sequence(self):
        if self.env.ref('delivery_dhl.dhl_commercial_invoice_seq').id in self.ids:
            raise UserError(_('You cannot delete the commercial invoice sequence.'))

    def _compute_can_generate_return(self):
        super(Providerdhl, self)._compute_can_generate_return()
        for carrier in self:
            if carrier.delivery_type == 'dhl':
                carrier.can_generate_return = True

    def _compute_supports_shipping_insurance(self):
        super(Providerdhl, self)._compute_supports_shipping_insurance()
        for carrier in self:
            if carrier.delivery_type == 'dhl':
                carrier.supports_shipping_insurance = True

    def dhl_rate_shipment(self, order):
        res = self._rate_shipment_vals(order=order)
        return res

    def _rate_shipment_vals(self, order=False, picking=False):
        if picking:
            warehouse_partner_id = picking.picking_type_id.warehouse_id.partner_id
            currency_id = picking.sale_id.currency_id or picking.company_id.currency_id
            destination_partner_id = picking.partner_id
            total_value = sum(sml.sale_price for sml in picking.move_line_ids)
        else:
            warehouse_partner_id = order.warehouse_id.partner_id
            currency_id = order.currency_id or order.company_id.currency_id
            total_value = sum(line.price_reduce_taxinc * line.product_uom_qty for line in order.order_line.filtered(lambda l: l.product_id.type == 'consu' and not l.display_type))
            destination_partner_id = order.partner_shipping_id

        rating_request = {}
        srm = DHLProvider(self.log_xml, request_type="rate", prod_environment=self.prod_environment)
        check_value = srm.check_required_value(self, destination_partner_id, warehouse_partner_id, order=order, picking=picking)
        if check_value:
            return {'success': False,
                    'price': 0.0,
                    'error_message': check_value,
                    'warning_message': False}
        site_id = self.sudo().dhl_SiteID
        password = self.sudo().dhl_password
        rating_request['Request'] = srm._set_request(site_id, password)
        rating_request['From'] = srm._set_dct_from(warehouse_partner_id)
        if picking:
            packages = self._get_packages_from_picking(picking, self.dhl_default_package_type_id)
        else:
            packages = self._get_packages_from_order(order, self.dhl_default_package_type_id)
        rating_request['BkgDetails'] = srm._set_dct_bkg_details(self, packages)
        rating_request['To'] = srm._set_dct_to(destination_partner_id)
        if self.dhl_dutiable:
            rating_request['Dutiable'] = srm._set_dct_dutiable(total_value, currency_id.name)
        real_rating_request = {}
        real_rating_request['GetQuote'] = rating_request
        real_rating_request['schemaVersion'] = 2.0
        self._dhl_add_custom_data_to_request(rating_request, 'rate')
        response = srm._process_rating(real_rating_request)

        available_product_code = []
        shipping_charge = False
        qtd_shp = response.findall('GetQuoteResponse/BkgDetails/QtdShp')
        if qtd_shp:
            for q in qtd_shp:
                charge = q.find('ShippingCharge').text
                global_product_code = q.find('GlobalProductCode').text
                if global_product_code == self.dhl_product_code and charge:
                    shipping_charge = charge
                    shipping_currency = q.find('CurrencyCode')
                    shipping_currency = None if shipping_currency is None else shipping_currency.text
                    break
                else:
                    available_product_code.append(global_product_code)
        else:
            condition = response.find('GetQuoteResponse/Note/Condition')
            if condition:
                condition_code = condition.find('ConditionCode').text
                if condition_code == '410301':
                    return {
                        'success': False,
                        'price': 0.0,
                        'error_message': "%s.\n%s" % (condition.find('ConditionData').text, _("Hint: The destination may not require the dutiable option.")),
                        'warning_message': False,
                    }
                elif condition_code in ['420504', '420505', '420506', '410304'] or\
                        response.find('GetQuoteResponse/Note/ActionStatus').text == "Failure":
                    return {
                        'success': False,
                        'price': 0.0,
                        'error_message': "%s." % (condition.find('ConditionData').text),
                        'warning_message': False,
                    }
        if shipping_charge:
            if order:
                order_currency = order.currency_id
            else:
                order_currency = picking.sale_id.currency_id or picking.company_id.currency_id
            if shipping_currency is None or order_currency.name == shipping_currency:
                price = float(shipping_charge)
            else:
                quote_currency = self.env['res.currency'].search([('name', '=', shipping_currency)], limit=1)
                price = quote_currency._convert(float(shipping_charge), order_currency, (order or picking).company_id, order.date_order if order else fields.Date.today())
            return {'success': True,
                    'price': price,
                    'error_message': False,
                    'warning_message': False}

        if available_product_code:
            return {'success': False,
                    'price': 0.0,
                    'error_message': _(
                        "There is no price available for this shipping, you should rather try with the DHL product %s",
                        available_product_code[0]),
                    'warning_message': False}

    def dhl_send_shipping(self, pickings):
        res = []
        for picking in pickings:
            shipment_request = {}
            srm = DHLProvider(self.log_xml, request_type="ship", prod_environment=self.prod_environment)
            site_id = self.sudo().dhl_SiteID
            password = self.sudo().dhl_password
            account_number = self.sudo().dhl_account_number
            shipment_request['Request'] = srm._set_request(site_id, password)
            shipment_request['RegionCode'] = srm._set_region_code(self.dhl_region_code)
            shipment_request['RequestedPickupTime'] = srm._set_requested_pickup_time(True)
            shipment_request['Billing'] = srm._set_billing(account_number, "S", self.dhl_duty_payment, self.dhl_dutiable)
            shipment_request['Consignee'] = srm._set_consignee(picking.partner_id)
            shipment_request['Shipper'] = srm._set_shipper(account_number, picking.company_id.partner_id, picking.picking_type_id.warehouse_id.partner_id)
            shipment_request['Reference'] = {
                'ReferenceID': picking.sale_id.name if picking.sale_id else picking.name,
                'ReferenceType': 'CU'
            }
            total_value, currency_name = self._dhl_calculate_value(picking)
            if self.dhl_dutiable:
                incoterm = picking.sale_id.incoterm or self.env.company.incoterm_id
                shipment_request['Dutiable'] = srm._set_dutiable(total_value, currency_name, incoterm)
            if picking._should_generate_commercial_invoice():
                shipment_request['UseDHLInvoice'] = 'Y'
                shipment_request['DHLInvoiceType'] = 'CMI'
                shipment_request['ExportDeclaration'] = srm._set_export_declaration(self, picking)
            shipment_request['ShipmentDetails'] = srm._set_shipment_details(picking)
            shipment_request['LabelImageFormat'] = srm._set_label_image_format(self.dhl_label_image_format)
            shipment_request['Label'] = srm._set_label(self.dhl_label_template)
            shipment_request['schemaVersion'] = 10.0
            shipment_request['LanguageCode'] = 'en'
            if picking.carrier_id.shipping_insurance:
                shipment_request['SpecialService'] = []
                shipment_request['SpecialService'].append(srm._set_insurance(shipment_request['ShipmentDetails']))
            self._dhl_add_custom_data_to_request(shipment_request, 'ship')
            dhl_response = srm._process_shipment(shipment_request)
            traking_number = dhl_response.AirwayBillNumber
            logmessage = Markup(_("Shipment created into DHL <br/> <b>Tracking Number: </b>%s")) % (traking_number)
            dhl_labels = [('%s-%s.%s' % (self._get_delivery_label_prefix(), traking_number, self.dhl_label_image_format), dhl_response.LabelImage[0].OutputImage)]
            dhl_cmi = [('%s-%s.%s' % (self._get_delivery_doc_prefix(), mlabel.DocName, mlabel.DocFormat), mlabel.DocImageVal) for mlabel in dhl_response.LabelImage[0].MultiLabels.MultiLabel] if dhl_response.LabelImage[0].MultiLabels else None
            lognote_pickings = picking
            if picking.sale_id:
                lognote_pickings |= picking.sale_id.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
            for pick in lognote_pickings:
                pick.message_post(body=logmessage, attachments=dhl_labels)
                if dhl_cmi:
                    pick.message_post(body=_("DHL Documents"), attachments=dhl_cmi)
            shipping_data = {
                'exact_price': 0,
                'tracking_number': traking_number,
            }
            rate = self._rate_shipment_vals(picking=picking)
            shipping_data['exact_price'] = rate['price']
            if self.return_label_on_delivery:
                self.get_return_label(picking)
            res = res + [shipping_data]

        return res

    def dhl_get_return_label(self, picking, tracking_number=None, origin_date=None):
        shipment_request = {}
        srm = DHLProvider(self.log_xml, request_type="ship", prod_environment=self.prod_environment)
        site_id = self.sudo().dhl_SiteID
        password = self.sudo().dhl_password
        account_number = self.sudo().dhl_account_number
        shipment_request['Request'] = srm._set_request(site_id, password)
        shipment_request['RegionCode'] = srm._set_region_code(self.dhl_region_code)
        shipment_request['RequestedPickupTime'] = srm._set_requested_pickup_time(True)
        shipment_request['Billing'] = srm._set_billing(account_number, "S", "S", self.dhl_dutiable)
        shipment_request['Consignee'] = srm._set_consignee(picking.picking_type_id.warehouse_id.partner_id)
        shipment_request['Shipper'] = srm._set_shipper(account_number, picking.partner_id, picking.partner_id)
        total_value, currency_name = self._dhl_calculate_value(picking)
        if self.dhl_dutiable:
            incoterm = picking.sale_id.incoterm or self.env.company.incoterm_id
            shipment_request['Dutiable'] = srm._set_dutiable(total_value, currency_name, incoterm)
        if picking._should_generate_commercial_invoice():
            shipment_request['UseDHLInvoice'] = 'Y'
            shipment_request['DHLInvoiceType'] = 'CMI'
            shipment_request['ExportDeclaration'] = srm._set_export_declaration(self, picking, is_return=True)
        shipment_request['ShipmentDetails'] = srm._set_shipment_details(picking)
        shipment_request['LabelImageFormat'] = srm._set_label_image_format(self.dhl_label_image_format)
        shipment_request['Label'] = srm._set_label(self.dhl_label_template)
        shipment_request['SpecialService'] = []
        shipment_request['SpecialService'].append(srm._set_return())
        shipment_request['schemaVersion'] = 10.0
        shipment_request['LanguageCode'] = 'en'
        self._dhl_add_custom_data_to_request(shipment_request, 'return')
        dhl_response = srm._process_shipment(shipment_request)
        traking_number = dhl_response.AirwayBillNumber
        logmessage = Markup(_("Shipment created into DHL <br/> <b>Tracking Number: </b>%s")) % (traking_number)
        dhl_labels = [('%s-%s-%s.%s' % (self.get_return_label_prefix(), traking_number, 1, self.dhl_label_image_format), dhl_response.LabelImage[0].OutputImage)]
        dhl_cmi = [('%s-Return-%s.%s' % (self._get_delivery_doc_prefix(), mlabel.DocName, mlabel.DocFormat), mlabel.DocImageVal) for mlabel in dhl_response.LabelImage[0].MultiLabels.MultiLabel] if dhl_response.LabelImage[0].MultiLabels else None
        lognote_pickings = picking.sale_id.picking_ids if picking.sale_id else picking
        for pick in lognote_pickings:
            pick.message_post(body=logmessage, attachments=dhl_labels)
            if dhl_cmi:
                pick.message_post(body=_("DHL Documents"), attachments=dhl_cmi)
        shipping_data = {
            'exact_price': 0,
            'tracking_number': traking_number,
        }
        return shipping_data

    def dhl_get_tracking_link(self, picking):
        return 'http://www.dhl.com/en/express/tracking.html?AWB=%s' % picking.carrier_tracking_ref

    def dhl_cancel_shipment(self, picking):
        # Obviously you need a pick up date to delete SHIPMENT by DHL. So you can't do it if you didn't schedule a pick-up.
        picking.message_post(body=_(u"You can't cancel DHL shipping without pickup date."))
        picking.write({'carrier_tracking_ref': '',
                       'carrier_price': 0.0})

    def _dhl_convert_weight(self, weight, unit):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        if unit == 'L':
            weight = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'), round=False)
        else:
            weight = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_kgm'), round=False)
        return float_repr(weight, 3)

    def _dhl_add_custom_data_to_request(self, request, request_type):
        """Adds the custom data to the request.
        When there are multiple items in a list, they will all be affected by
        the change.
        for example, with
        {"ShipmentDetails": {"Pieces": {"Piece": {"AdditionalInformation": "custom info"}}}}
        the AdditionalInformation of each piece will be updated.
        """
        if not self.dhl_custom_data_request:
            return
        try:
            custom_data = const_eval('{%s}' % self.dhl_custom_data_request).get(request_type, {})
        except SyntaxError:
            raise UserError(_('Invalid syntax for DHL custom data.'))

        def extra_data_to_request(request, custom_data):
            """recursive function that adds custom data to the current request."""
            for key, new_value in custom_data.items():
                request[key] = current_value = serialize_object(request.get(key, {})) or None
                if isinstance(current_value, list):
                    for item in current_value:
                        extra_data_to_request(item, new_value)
                elif isinstance(new_value, dict) and isinstance(current_value, dict):
                    extra_data_to_request(current_value, new_value)
                else:
                    request[key] = new_value

        extra_data_to_request(request, custom_data)

    def _dhl_calculate_value(self, picking):
        sale_order = picking.sale_id
        if sale_order:
            total_value = sum(line.price_reduce_taxinc * line.product_uom_qty for line in
                              sale_order.order_line.filtered(
                                  lambda l: l.product_id.type == 'consu' and not l.display_type))
            currency_name = picking.sale_id.currency_id.name
        else:
            total_value = sum([line.product_id.lst_price * line.product_qty for line in picking.move_ids])
            currency_name = picking.company_id.currency_id.name
        return total_value, currency_name
