# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import json
from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round, float_is_zero
from odoo.tools.misc import groupby

from .usps_request import USPSRequest, split_zip

HELP_EXTRA_DATA = """Extra data to be sent in the request. It should be a JSON-formatted string. For example:
This functionality is advanced/technical and should only be used if you know what you are doing.
Example of a valid value: ```
"packageDescription": {"extraServices": [920] }
```
With the above example, the service (920) will be added to the shipment request.
For more information, please refer to the USS API documentation: https://developer.usps.com/apis.
"""


class ProviderUSPS(models.Model):
    _inherit = 'delivery.carrier'

    delivery_type = fields.Selection(selection_add=[
        ('usps_rest', "USPS")
    ], ondelete={'usps_rest': lambda recs: recs.write({'delivery_type': 'fixed', 'fixed_price': 0})})
    # Fields required to configure
    usps_eps_account_number = fields.Char(string='EPS Account Number', groups="base.group_system")
    usps_crid = fields.Char(string='CRID', groups="base.group_system")
    usps_mid = fields.Char(string='MID', groups="base.group_system")
    usps_manifest_mid = fields.Char(string='Manifest MID', groups="base.group_system")
    usps_api_key = fields.Char(string='USPS API Key', groups="base.group_system")
    usps_api_secret = fields.Char(string='USPS API Secret', groups="base.group_system")
    usps_access_token = fields.Char(string='USPS Access Token', groups="base.group_system")
    usps_payment_token = fields.Char(string='USPS Payment Token', groups="base.group_system")
    usps_delivery_nature = fields.Selection([('domestic', 'Domestic'),
                                             ('international', 'International')],
                                            string="Delivery Nature", default='domestic', required=True)
    usps_default_package_type_id = fields.Many2one('stock.package.type', string="USPS Package Type")
    usps_rest_label_file_type = fields.Selection([('PDF', 'PDF'),
                                             ('TIFF', 'TIFF'),
                                             ('JPG', 'JPG'),
                                             ('SVG', 'SVG')],
                                            string="USPS Label File Type", default='PDF')
    usps_label_size = fields.Selection([('4X6LABEL', '4x6'),
                                        ('4X5LABEL', '4x5'),
                                        ('3X5FMP', '3x5')], string="USPS Label Size", default='4X6LABEL')
    usps_domestic_service = fields.Selection([('PARCEL_SELECT', 'Parcel Select'),
                                              ('PARCEL_SELECT_LIGHTWEIGHT', 'Parcel Select Lightweight'),
                                              ('PRIORITY_MAIL_EXPRESS', 'Priority Mail Express'),
                                              ('PRIORITY_MAIL', 'Priority Mail'),
                                              ('FIRST-CLASS_PACKAGE_SERVICE', 'First-Class Package Service'),
                                              ('LIBRARY_MAIL', 'Library Mail'),
                                              ('MEDIA_MAIL', 'Media Mail'),
                                              ('BOUND_PRINTED_MATTER', 'Bound Printed Matter'),
                                              ('USPS_CONNECT_LOCAL', 'USPS Connect Local'),
                                              ('USPS_CONNECT_MAIL', 'USPS Connect Mail'),
                                              ('USPS_CONNECT_NEXT_DAY', 'USPS Connect Next Day'),
                                              ('USPS_CONNECT_REGIONAL', 'USPS Connect Regional'),
                                              ('USPS_CONNECT_SAME_DAY', 'USPS Connect Same Day'),
                                              ('USPS_GROUND_ADVANTAGE', 'USPS Ground Advantage'),
                                              ('USPS_GROUND_ADVANTAGE_RETURN_SERVICE', 'USPS Ground Advantage Return Service'),
                                              ('USPS_RETAIL_GROUND', 'USPS Retail Ground')],
                                             string="USPS Domestic Service", default="PARCEL_SELECT")
    usps_international_service = fields.Selection([('FIRST-CLASS_PACKAGE_INTERNATIONAL_SERVICE', 'First-Class Package International Service'),
                                                   ('PRIORITY_MAIL_INTERNATIONAL', 'Priority Mail International'),
                                                   ('PRIORITY_MAIL_EXPRESS_INTERNATIONAL', 'Priority Mail Express International'),
                                                   ('GLOBAL_EXPRESS_GUARANTEED', 'Global Express Guaranteed')],
                                                  string="USPS International Service", default="PRIORITY_MAIL_INTERNATIONAL")
    usps_rest_content_type = fields.Selection([('MERCHANDISE', 'Merchandise'),
                                          ('SAMPLE', 'Sample'),
                                          ('GIFT', 'Gift'),
                                          ('DOCUMENT', 'Document'),
                                          ('COMMERCIAL_SAMPLE', 'Commercial Sample'),
                                          ('RETURNED_GOODS', 'Returned Goods'),
                                          ('HUMANITARIAN_DONATIONS', 'Humanitarian Donations'),
                                          ('DANGEROUS_GOODS', 'Dangerous Goods'),
                                          ('CREMATED_REMAINS', 'Cremated Remains'),
                                          ('NON_NEGOTIABLE_DOCUMENT', 'Non-Negotiable Document'),
                                          ('MEDICAL_SUPPLIES', 'Medical Supplies'),
                                          ('PHARMACEUTICALS', 'Pharmaceuticals'),
                                          ('OTHER', 'Other')],
                                         default='MERCHANDISE', string="Content Type (REST)")
    usps_domestic_rating_indicator = fields.Selection([('3D', '3D - 3-Digit'),
                                                       ('3N', '3N - 3-Digit Dimensional Rectangular'),
                                                       ('3R', '3R - 3-Digit Dimensional Nonrectangular'),
                                                       ('5D', '5D - 5-Digit'),
                                                       ('BA', 'BA - Basic'),
                                                       ('BB', 'BB - Mixed NDC'),
                                                       ('CP', 'CP - Cubic Parcel'),
                                                       ('CM', 'CM - USPS Connect® Local Mail'),
                                                       ('DC', 'DC - NDC'),
                                                       ('DE', 'DE - SCF'),
                                                       ('DF', 'DF - 5-Digit'),
                                                       ('DN', 'DN - Dimensional Nonrectangular'),
                                                       ('DR', 'DR - Dimensional Rectangular'),
                                                       ('E4', 'E4 - Priority Mail Express Flat Rate Envelope - Post Office To Addressee'),
                                                       ('E6', 'E6 - Priority Mail Express Legal Flat Rate Envelope'),
                                                       ('FA', 'FA - Legal Flat Rate Envelope'),
                                                       ('FB', 'FB - Medium Flat Rate Box/Large Flat Rate Bag'),
                                                       ('FE', 'FE - Flat Rate Envelope'),
                                                       ('FP', 'FP - Padded Flat Rate Envelope'),
                                                       ('FS', 'FS - Small Flat Rate Box'),
                                                       ('LC', 'LC - USPS Connect® Local Single Piece'),
                                                       ('LF', 'LF - Flat Rate Box'),
                                                       ('LL', 'LL - Large Flat Rate Bag'),
                                                       ('LO', 'LO - USPS Connect® Local Oversized'),
                                                       ('LS', 'LS - Small Flat Rate Bag'),
                                                       ('NP', 'NP - Non-Presorted'),
                                                       ('OS', 'OS - Oversized'),
                                                       ('P5', 'P5 - Cubic Soft Pack Tier 1'),
                                                       ('P6', 'P6 - Cubic Soft Pack Tier 2'),
                                                       ('P7', 'P7 - Cubic Soft Pack Tier 3'),
                                                       ('P8', 'P8 - Cubic Soft Pack Tier 4'),
                                                       ('P9', 'P9 - Cubic Soft Pack Tier 5'),
                                                       ('Q6', 'Q6 - Cubic Soft Pack Tier 6'),
                                                       ('Q7', 'Q7 - Cubic Soft Pack Tier 7'),
                                                       ('Q8', 'Q8 - Cubic Soft Pack Tier 8'),
                                                       ('Q9', 'Q9 - Cubic Soft Pack Tier 9'),
                                                       ('Q0', 'Q0 - Cubic Soft Pack Tier 10'),
                                                       ('PA', 'PA - Priority Mail Express Single Piece'),
                                                       ('PL', 'PL - Large Flat Rate Box'),
                                                       ('PM', 'PM - Large Flat Rate Box APO/FPO/DPO'),
                                                       ('PR', 'PR - Presorted'),
                                                       ('SN', 'SN - SCF Dimensional Nonrectangular'),
                                                       ('SP', 'SP - Single Piece'),
                                                       ('SR', 'SR - SCF Dimensional Rectangular')], string="Domestic Rating Indicator")
    usps_international_rating_indicator = fields.Selection([('E4', 'E4 - Priority Mail Express Flat Rate Envelope - Post Office To Addressee'),
                                                            ('E6', 'E6 - Priority Mail Express Legal Flat Rate Envelope'),
                                                            ('E7', 'E7 - Priority Mail Express Legal Flat Rate Envelope Sunday / Holiday'),
                                                            ('FA', 'FA - Legal Flat Rate Envelope'),
                                                            ('FB', 'FB - Medium Flat Rate Box/Large Flat Rate Bag'),
                                                            ('FE', 'FE - Flat Rate Envelope'),
                                                            ('FP', 'FP - Padded Flat Rate Envelope'),
                                                            ('FS', 'FS - Small Flat Rate Box'),
                                                            ('PA', 'PA - Priority Mail Express International Single Piece'),
                                                            ('PL', 'PL - Large Flat Rate Box'),
                                                            ('SP', 'SP - Single Piece')
                                                            ], string="International Rating Indicator")
    usps_processing_category = fields.Selection([('LETTERS', 'Letters'),
                                                 ('FLATS', 'Flats'),
                                                 ('MACHINABLE', 'Machinable'),
                                                 ('IRREGULAR', 'Irregular'),
                                                 ('NON_MACHINABLE', 'Non-Machinable')],
                                                string="Processing Category", help="Please check on USPS website to check your package processing category")
    usps_extra_data_rate_request = fields.Text('Extra Data for Rate Requests', help=HELP_EXTRA_DATA)
    usps_extra_data_shipment_request = fields.Text('Extra Data for Shipment Requests', help=HELP_EXTRA_DATA)
    usps_extra_data_payment_token_request = fields.Text('Extra Data for Payment Token Requests', help=HELP_EXTRA_DATA)

    @api.depends('usps_delivery_nature')
    def _compute_can_generate_return(self):
        super()._compute_can_generate_return()
        for carrier in self:
            if carrier.delivery_type == 'usps_rest':
                if carrier.usps_delivery_nature == 'international':
                    carrier.can_generate_return = False
                else:
                    carrier.can_generate_return = True

    def _usps_convert_weight(self, weight):
        weight_uom_id = self.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
        weight_in_pounds = weight_uom_id._compute_quantity(weight, self.env.ref('uom.product_uom_lb'))
        return weight_in_pounds

    def _usps_convert_length(self, length):
        length_uom_id = self.env['product.template']._get_length_uom_id_from_ir_config_parameter()
        length_in_inches = length_uom_id._compute_quantity(length, self.env.ref('uom.product_uom_inch'))
        return length_in_inches

    def _get_order_packages(self, order):
        self.ensure_one()
        if self.delivery_type != 'usps_rest':
            # Method will be renamed in master so that it doesn't clash with delivery_dhl_rest
            return super()._get_order_packages(order)

        total_weight = order._get_estimated_weight()
        if float_is_zero(total_weight, precision_rounding=0.01):
            weight_uom_name = self.env['product.template']._get_weight_uom_name_from_ir_config_parameter()
            raise UserError(_("The package cannot be created because the total weight of the products in the picking is 0.0 %s", weight_uom_name))
        total_weight = self._usps_convert_weight(total_weight)

        max_weight = self.usps_default_package_type_id.max_weight or total_weight + 1
        number_of_packages = int(total_weight / max_weight)
        last_package_weight = total_weight % max_weight

        weights = [max_weight] * number_of_packages + ([last_package_weight] if last_package_weight else [])
        return [{
            'weight': weight,
            'dimension': {
                'length': self.usps_default_package_type_id.packaging_length,
                'width': self.usps_default_package_type_id.width,
                'height': self.usps_default_package_type_id.height,
            },
        } for weight in weights]

    def usps_rest_rate_shipment(self, order):
        srm = USPSRequest(self)

        check_result = srm.check_required_value(order.partner_shipping_id, self.usps_delivery_nature, order.warehouse_id.partner_id, order=order)
        if check_result:
            return {'success': False, 'price': 0.0, 'error_message': check_result, 'warning_message': False}

        packages = self._get_order_packages(order)
        quotes_list = []
        for package in packages:
            request_body = {
                'originZIPCode': split_zip(order.warehouse_id.partner_id.zip)[0],
                'weight': package['weight'],
                'length': self._usps_convert_length(package['dimension']['length']),
                'width': self._usps_convert_length(package['dimension']['width']),
                'height': self._usps_convert_length(package['dimension']['height']),
                'accountType': 'EPS',
                'accountNumber': self.sudo().usps_eps_account_number,
                'mailingDate': order.date_order.strftime('%Y-%m-%d'),
            }
            if self.usps_delivery_nature == 'domestic':
                request_body['destinationZIPCode'] = split_zip(order.partner_shipping_id.zip)[0]
            else:
                request_body['destinationCountryCode'] = order.partner_shipping_id.country_id.code
                request_body['foreignPostalCode'] = order.partner_shipping_id.zip

            self._usps_add_extra_data_to_request(request_body, 'rate')
            rates_response = srm._get_rates(request_body)
            quotes_list.append(rates_response.get('rateOptions', []))

        price = 0
        mail_class = self.usps_domestic_service if self.usps_delivery_nature == 'domestic' else self.usps_international_service
        mc_exists_for_all_packages = True
        for quotes in quotes_list:
            mc_exists = False
            for quote in quotes:
                if quote.get('rates')[0].get('mailClass') == mail_class:
                    price += quote.get('totalBasePrice')
                    mc_exists = True
                    break
            if not mc_exists:
                mc_exists_for_all_packages = False
                break
        if mc_exists_for_all_packages:
            if order.currency_id.name == 'USD':
                return {'success': True, 'price': price, 'error_message': False, 'warning_message': False}
            else:
                quote_currency = self.env['res.currency'].search([('name', '=', 'USD')], limit=1)
                price = quote_currency._convert(price, order.currency_id, order.company_id, order.date_order or fields.Date.today())
                return {'success': True, 'price': price, 'error_message': False, 'warning_message': False}
        else:
            return {
                'success': False,
                'price': 0.0,
                'error_message': _("There is no price available for this shipping, please choose another service"),
                'warning_message': False
            }

    def _usps_rest_get_commodities_from_stock_move_lines(self, move_lines):
        commodities = []

        product_lines = move_lines.filtered(lambda line: line.product_id.type in ['product', 'consu'])
        for product, lines in groupby(product_lines, lambda x: x.product_id):
            unit_quantity = sum(
                line.product_uom_id._compute_quantity(
                    line.quantity,
                    product.uom_id)
                for line in lines)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0))
            country_of_origin = lines[0].picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            unit_price = sum(line.sale_price for line in lines) / rounded_qty
            commodities.append({
                'product_id': product,
                'qty': rounded_qty,
                'monetary_value': unit_price,
                'country_of_origin': country_of_origin
            })

        return commodities

    def _get_picking_packages(self, picking):
        self.ensure_one()
        if self.delivery_type != 'usps_rest':
            # Method will be renamed in master so that it doesn't clash with delivery_dhl_rest
            return super()._get_picking_packages(picking)
        packages = []

        if picking.is_return_picking:
            commodities = self._usps_rest_get_commodities_from_stock_move_lines(picking.move_line_ids)
            weight = picking._get_estimated_weight()
            packages.append({
                'commodities': commodities,
                'weight': weight,
                'dimension': {
                    'length': self.usps_default_package_type_id.packaging_length,
                    'width': self.usps_default_package_type_id.width,
                    'height': self.usps_default_package_type_id.height,
                },
            })
            return packages

        # Create all packages.
        for package in picking.move_line_ids.result_package_id:
            move_lines = picking.move_line_ids.filtered(lambda ml: ml.result_package_id == package)
            commodities = self._usps_rest_get_commodities_from_stock_move_lines(move_lines)
            packages.append({
                'commodities': commodities,
                'weight': package.shipping_weight or package.weight,
                'dimension': {
                    'length': package.package_type_id.packaging_length,
                    'width': package.package_type_id.width,
                    'height': package.package_type_id.height,
                },
            })

        # Create one package: either everything is in pack or nothing is.
        if picking.weight_bulk:
            commodities = self._usps_rest_get_commodities_from_stock_move_lines(picking.move_line_ids)
            packages.append({
                'commodities': commodities,
                'weight': picking.weight_bulk,
                'dimension': {
                    'length': self.usps_default_package_type_id.packaging_length,
                    'width': self.usps_default_package_type_id.width,
                    'height': self.usps_default_package_type_id.height,
                },
            })
        elif not packages:
            raise UserError(_(
                "The package cannot be created because the total weight of the "
                "products in the picking is 0.0 %s",
                picking.weight_uom_name
            ))
        return packages

    def usps_rest_send_shipping(self, pickings):
        res = []
        srm = USPSRequest(self)
        for picking in pickings:
            check_result = srm.check_required_value(picking.partner_id, self.usps_delivery_nature, picking.picking_type_id.warehouse_id.partner_id, picking=picking)
            if check_result:
                raise UserError(check_result)

            image_info = {
                'imageType': self.usps_rest_label_file_type,
                'labelType': self.usps_label_size,
            }
            if self.return_label_on_delivery and self.usps_delivery_nature == 'domestic':
                image_info.update({
                    'returnLabel': True,
                })
            to_address = {
                'streetAddress': picking.partner_id.street,
                'secondaryAddress': picking.partner_id.street2 or '',
                'city': picking.partner_id.city,
                'state': picking.partner_id.state_id.code,
                'ZIPCode': split_zip(picking.partner_id.zip)[0],
                'ZIPPlus4': split_zip(picking.partner_id.zip)[1] or None,
                'firstName': picking.partner_id.name or '.',
                'lastName': picking.partner_id.company_name or '.',
            }
            if self.usps_delivery_nature == 'international':
                to_address.update({
                    'country': picking.partner_id.country_id.name,
                    'countryISOAlpha2Code': picking.partner_id.country_id.code,
                })
            from_address = {
                'streetAddress': picking.picking_type_id.warehouse_id.partner_id.street,
                'secondaryAddress': picking.picking_type_id.warehouse_id.partner_id.street2 or '',
                'city': picking.picking_type_id.warehouse_id.partner_id.city,
                'state': picking.picking_type_id.warehouse_id.partner_id.state_id.code,
                'ZIPCode': split_zip(picking.picking_type_id.warehouse_id.partner_id.zip)[0],
                'ZIPPlus4': split_zip(picking.picking_type_id.warehouse_id.partner_id.zip)[1] or None,
                'firstName': picking.picking_type_id.warehouse_id.partner_id.name or '.',
                'lastName': picking.picking_type_id.warehouse_id.partner_id.company_name or '.',
            }
            customs_form = {
                'AESITN': 'XYZ',
                'customsContentType': self.usps_rest_content_type,
            }

            packages = self._get_picking_packages(picking)
            shipping_data = {
                'exact_price': [],
                'tracking_number': [],
            }
            for package in packages:
                package_description = {
                    'mailClass': self.usps_domestic_service if self.usps_delivery_nature == 'domestic' else self.usps_international_service,
                    'weightUOM': 'lb',
                    'weight': self._usps_convert_weight(package['weight']),
                    'dimensionUOM': 'in',
                    'length': self._usps_convert_length(package['dimension']['length']),
                    'width': self._usps_convert_length(package['dimension']['width']),
                    'height': self._usps_convert_length(package['dimension']['height']),
                    'rateIndicator': self.usps_domestic_rating_indicator if self.usps_delivery_nature == 'domestic' else self.usps_international_rating_indicator,
                    'processingCategory': self.usps_processing_category,
                    'destinationEntryFacilityType': 'NONE',
                    'mailingDate': picking.scheduled_date.strftime('%Y-%m-%d'),
                }
                shipping_request = {
                    'imageInfo': image_info,
                    'fromAddress': from_address,
                    'toAddress': to_address,
                    'packageDescription': package_description,
                }
                if self.usps_delivery_nature == 'international':
                    customs_form.update({
                        'contents': [{
                            'itemDescription': commodity['product_id'].name,
                            'itemQuantity': int(commodity['qty']),
                            'countryofOrigin': commodity['country_of_origin'],
                            'itemTotalValue': commodity['monetary_value'],
                            'itemTotalWeight': commodity['product_id'].weight * commodity['qty'],
                            'HSTariffNumber': commodity['product_id'].hs_code or '      ',
                        } for commodity in package['commodities']]
                    })
                    shipping_request.update({
                        'customsForm': customs_form,
                    })

                self._usps_add_extra_data_to_request(shipping_request, 'shipment')
                shipping_response = srm._get_shipping_label(shipping_request)

                label_info = shipping_response.get('labelMetadata', {})
                tracking_number = label_info.get('trackingNumber') or label_info.get('internationalTrackingNumber')
                log_message = (_("Shipment created into USPS") + Markup("<br/><b>") + _("Tracking Number:") + Markup("</b> ") + tracking_number)
                usps_label = ('%s-%s.%s' % ('LabelShipping-USPS', tracking_number, self.usps_rest_label_file_type), base64.b64decode(shipping_response.get('labelImage')))
                if self.return_label_on_delivery and self.usps_delivery_nature == 'domestic':
                    return_label_info = shipping_response.get('returnLabelMetadata', {})
                    return_tracking_number = return_label_info.get('trackingNumber')
                    return_usps_label = ('%s-%s.%s' % ('LabelReturn-USPS', return_tracking_number, self.usps_rest_label_file_type), base64.b64decode(shipping_response.get('returnLabelImage')))
                    return_log_message = (_("Return Shipment created into USPS") + Markup("<br/><b>") + _("Tracking Number:") + Markup("</b> ") + return_tracking_number)
                lognote_pickings = picking.sale_id.picking_ids if picking.sale_id else picking
                for pick in lognote_pickings:
                    pick.message_post(body=log_message, attachments=[usps_label])
                    if self.return_label_on_delivery and self.usps_delivery_nature == 'domestic':
                        pick.message_post(body=return_log_message, attachments=[return_usps_label])
                shipping_data['tracking_number'].append(tracking_number)
                shipping_data['exact_price'].append(label_info.get('postage'))
                if label_info.get('fees'):
                    shipping_data['exact_price'][-1] += sum(fee.get('price') for fee in label_info.get('fees'))
                if label_info.get('extraServices'):
                    shipping_data['exact_price'][-1] += sum(service.get('price') for service in label_info.get('extraServices'))
            res.append({
                'exact_price': sum(shipping_data['exact_price']),
                'tracking_number': ', '.join(shipping_data['tracking_number']),
            })
        return res

    def usps_rest_get_tracking_link(self, picking):
        return 'https://tools.usps.com/go/TrackConfirmAction?tLabels=%s' % picking.carrier_tracking_ref

    def usps_rest_cancel_shipment(self, picking):
        srm = USPSRequest(self)
        result = srm._cancel_label(picking.carrier_tracking_ref)
        if result:
            picking.message_post(body=_("Shipment with tracking number %(tracking_ref)s has been cancelled", tracking_ref=picking.carrier_tracking_ref))
            picking.write({'carrier_tracking_ref': '', 'carrier_price': 0.0})

    def _usps_add_extra_data_to_request(self, request, request_type):
        """Adds the extra data to the request.
        When there are multiple items in a list, they will all be affected by
        the change.
        for example, with
        "roles": {"role": {"CRID": "12345"}}
        the CRID of each role will be updated."""
        extra_data_input = {
            'rate': self.usps_extra_data_rate_request,
            'shipment': self.usps_extra_data_shipment_request,
            'payment_token': self.usps_extra_data_payment_token_request,
        }.get(request_type) or ''
        try:
            extra_data = json.loads('{' + extra_data_input + '}')
        except SyntaxError:
            raise UserError(_("Invalid syntax for USPS extra data."))

        def extra_data_to_request(request, extra_data):
            """recursive method that adds the extra data to the current request"""
            for key, new_value in extra_data.items():
                request[key] = current_value = request.get(key)
                if isinstance(current_value, list):
                    for item in current_value:
                        extra_data_to_request(item, new_value)
                elif isinstance(new_value, dict) and isinstance(current_value, dict):
                    extra_data_to_request(current_value, new_value)
                else:
                    request[key] = new_value

        extra_data_to_request(request, extra_data)
