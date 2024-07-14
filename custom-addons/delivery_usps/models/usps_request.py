# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import binascii
import math
import re

import requests
from lxml import etree

from odoo import fields, _


# This re should match postcodes like 12345 and 12345-6789
ZIP_ZIP4 = re.compile('^[0-9]{5}(-[0-9]{4})?$')


def split_zip(zipcode):
    '''If zipcode is a ZIP+4, split it into two parts.
       Else leave it unchanged '''
    if ZIP_ZIP4.match(zipcode) and '-' in zipcode:
        return zipcode.split('-')
    else:
        return [zipcode, '']


class USPSRequest():

    def __init__(self, prod_environment, debug_logger):
        self.debug_logger = debug_logger
        if not prod_environment:
            self.url = 'https://stg-secure.shippingapis.com/ShippingAPI.dll'
        else:
            self.url = 'https://secure.shippingapis.com/ShippingAPI.dll'
        self.prod_environment = prod_environment

    def check_required_value(self, recipient, delivery_nature, shipper, order=False, picking=False):
        recipient_required_field = ['city', 'zip', 'country_id']
        # The street isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not recipient.street and not recipient.street2 and not recipient._context.get(
            'express_checkout_partial_delivery_address', False
        ):
            recipient_required_field.append('street')
        shipper_required_field = ['city', 'zip', 'phone', 'state_id', 'country_id']
        if not shipper.street and not shipper.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company is missing or wrong (Missing field(s) :  \n %s)", ", ".join(res).replace("_id", ""))
        if shipper.country_id.code != 'US':
            return _("Please set country U.S.A in your company address, Service is only available for U.S.A")
        if not ZIP_ZIP4.match(shipper.zip):
            return _("Please enter a valid ZIP code in your Company address")
        if not self._convert_phone_number(shipper.phone):
            return _("Company phone number is invalid. Please insert a US phone number.")
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The recipient address is missing or wrong (Missing field(s) :  \n %s)", ", ".join(res).replace("_id", ""))
        if delivery_nature == 'domestic' and not ZIP_ZIP4.match(recipient.zip):
            return _("Please enter a valid ZIP code in recipient address")
        if recipient.country_id.code == "US" and delivery_nature == 'international':
            return _("USPS International is used only to ship outside of the U.S.A. Please change the delivery method into USPS Domestic.")
        if recipient.country_id.code != "US" and delivery_nature == 'domestic':
            return _("USPS Domestic is used only to ship inside of the U.S.A. Please change the delivery method into USPS International.")
        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s", ", ".join(error_lines.product_id.mapped('name')))
            tot_weight = order._get_estimated_weight()
            weight_uom_id = order.env['product.template']._get_weight_uom_id_from_ir_config_parameter()
            weight_in_pounds = weight_uom_id._compute_quantity(tot_weight, order.env.ref('uom.product_uom_lb'))
            if weight_in_pounds > 4 and order.carrier_id.usps_service == 'First Class':     # max weight of FirstClass Service
                return _("Please choose another service (maximum weight of this service is 4 pounds)")
        if picking and picking.move_ids:
            # https://www.usps.com/business/web-tools-apis/evs-international-label-api.htm
            if max(picking.move_ids.mapped('product_uom_qty')) > 999:
                return _("Quantity for each move line should be less than 1000.")
        return False

    def _usps_request_data(self, carrier, order):
        currency = carrier.env['res.currency'].search([('name', '=', 'USD')], limit=1)  # USPS Works in USDollars
        tot_weight = order._get_estimated_weight()
        total_weight = carrier._usps_convert_weight(tot_weight)
        total_value = sum([(line.price_unit * line.product_uom_qty) for line in order.order_line.filtered(lambda line: not line.is_delivery and not line.display_type)]) or 0.0

        if order.currency_id.name == currency.name:
            price = total_value
        else:
            quote_currency = order.currency_id
            price = quote_currency._convert(
                total_value, currency, order.company_id, order.date_order or fields.Date.today())

        rate_detail = {
            'api': 'RateV4' if carrier.usps_delivery_nature == 'domestic' else 'IntlRateV2',
            'ID': carrier.sudo().usps_username,
            'revision': "2",
            'package_id': '%s%d' % ("PKG", order.id),
            'ZipOrigination': split_zip(order.warehouse_id.partner_id.zip)[0],
            'ZipDestination': split_zip(order.partner_shipping_id.zip)[0],
            'FirstClassMailType': carrier.usps_first_class_mail_type,
            'Pounds': total_weight['pound'],
            'Ounces': total_weight['ounce'],
            'Size': carrier.usps_size_container,
            'Service': carrier.usps_service,
            'Container': carrier.usps_container,
            'DomesticRegularontainer': carrier.usps_domestic_regular_container,
            'InternationalRegularContainer': carrier.usps_international_regular_container,
            'MailType': carrier.usps_mail_type,
            'Machinable': str(carrier.usps_machinable),
            'ValueOfContents': price,
            'Country': order.partner_shipping_id.country_id.name,
            'Width': carrier.usps_custom_container_width,
            'Height': carrier.usps_custom_container_height,
            'Length': carrier.usps_custom_container_length,
            'Girth': carrier.usps_custom_container_girth,
        }

        # Shipping to Canada requires additional information
        if order.partner_shipping_id.country_id.code == "CA":
            rate_detail.update(OriginZip=order.warehouse_id.partner_id.zip)

        return rate_detail

    def usps_rate_request(self, order, carrier):
        request_detail = self._usps_request_data(carrier, order)
        request_text = carrier.env['ir.qweb']._render('delivery_usps.usps_price_request', request_detail, inherit_branding=False)
        dict_response = {'price': 0.0, 'currency_code': "USD"}
        api = 'RateV4' if carrier.usps_delivery_nature == 'domestic' else 'IntlRateV2'

        try:
            self.debug_logger(request_text, 'usps_request_rate')
            req = requests.get(self.url, params={'API': api, 'XML': request_text})
            req.raise_for_status()
            response_text = req.content
            self.debug_logger(response_text, 'usps_response_rate')
        except IOError:
            dict_response['error_message'] = 'USPS Server Not Found - Check your connectivity'
            return dict_response
        root = etree.fromstring(response_text)
        errors_return = root.findall('.//Description')
        errors_number = root.findall('.//Number')
        if errors_return:
            dict_response['error_message'] = self._error_message(errors_number[0].text if errors_number else '', errors_return[0].text)
            return dict_response
        # Domestic Rate
        elif root.tag == 'RateV4Response':
            package_root = root.findall('Package')
            postage_roots = package_root[0].findall('Postage')
            for postage_root in postage_roots:
                rate = postage_root.findtext('Rate')
                dict_response['price'] = float(rate)
        # International Rate
        else:
            package_root = root.findall('Package')
            services = package_root[0].findall("Service")
            postages_prices = []
            for service in services:
                if carrier.usps_service in service.findall("SvcDescription")[0].text:
                    postages_prices += [float(service.findall("Postage")[0].text)]
            if not postages_prices:
                dict_response['error_message'] = _("The selected USPS service (%s) cannot be used to deliver this package.", carrier.usps_service)
                return dict_response
            else:
                dict_response['price'] = min(postages_prices)
        return dict_response

    def _item_data(self, line, weight, price):
        return {
            'Description': line.name,
            'Quantity': max(int(line.product_uom_qty), 1),  # the USPS API does not accept 1.0 but 1
            'Value': price,
            'NetPounds': weight['pound'],
            'NetOunces': round(weight['ounce'], 0),
            'CountryOfOrigin': line.warehouse_id.partner_id.country_id.name or ''
        }

    def _usps_shipping_data(self, picking, is_return=False):
        carrier = picking.carrier_id
        itemdetail = []

        api = self._api_url(carrier.usps_delivery_nature, carrier.usps_service)

        for line in picking.move_ids:
            USD = carrier.env['res.currency'].search([('name', '=', 'USD')], limit=1)
            order = picking.sale_id
            company = order.company_id or picking.company_id or self.env.company
            shipper_currency = picking.sale_id.currency_id or picking.company_id.currency_id
            if shipper_currency.name == USD.name:
                price = line.product_id.lst_price * line.product_uom_qty
            else:
                quote_currency = picking.env['res.currency'].search([('name', '=', shipper_currency.name)], limit=1)
                amount = line.product_id.lst_price * line.product_uom_qty
                price = quote_currency._convert(
                    amount, USD, company, order.date_order or fields.Date.today())
            weight = carrier._usps_convert_weight(line.product_id.weight * line.product_uom_qty)
            itemdetail.append(self._item_data(line, weight, price))

        if not is_return:
            gross_weight = carrier._usps_convert_weight(picking.shipping_weight)
            weight_in_ounces = 16 * gross_weight['pound'] + gross_weight['ounce']
        else:
            gross_weight = carrier._usps_convert_weight(picking._get_estimated_weight())
            weight_in_ounces = picking._get_estimated_weight() * 35.274
        shipping_detail = {
            'api': api,
            'ID': carrier.sudo().usps_username,
            'revision': '2' if carrier.usps_delivery_nature == 'international' else '',
            'ImageParameters': '',
            'picking_carrier': picking.carrier_id,
            'ToPOBoxFlag': 'N',
            'ToPOBoxFlagDom': 'false',
            'shipping': itemdetail,
            'GrossPounds': gross_weight['pound'],
            'GrossOunces': int(round(gross_weight['ounce'], 0)),    # API want 1 and no 1.0
            'MailType': carrier.usps_mail_type,
            'FirstClassMailType': 'LETTER',
            'ImageType': carrier.usps_label_file_type,
            'ImageLayout': 'ALLINONEFILE',
            'Size': carrier.usps_size_container,
            'ContentType': carrier.usps_content_type,
            'WeightInOunces': int(weight_in_ounces),
            'Agreement': 'Y',
            'Width': carrier.usps_custom_container_width,
            'Height': carrier.usps_custom_container_height,
            'Length': carrier.usps_custom_container_length,
            'Girth': carrier.usps_custom_container_girth,
            'ServiceType': carrier.usps_service,
            'domestic_regular_container': carrier.usps_domestic_regular_container,
            'UspsNonDeliveryOption': carrier.usps_intl_non_delivery_option,
            'AltReturnAddress1': carrier.usps_redirect_partner_id.street,
            'AltReturnAddress2': carrier.usps_redirect_partner_id.street2,
            'AltReturnAddress3': carrier.usps_redirect_partner_id.zip + " " + carrier.usps_redirect_partner_id.city if carrier.usps_redirect_partner_id else '',
            'AltReturnCountry': carrier.usps_redirect_partner_id.country_id.name,
            'Machinable': str(carrier.usps_machinable),
            'Container': carrier.usps_container,
            'IsReturn': is_return,
            # We pass the function so that the template can use it too
            'func_split_zip': split_zip,
        }
        if not is_return:
            shipping_detail.update({
                'picking_warehouse_partner': picking.picking_type_id.warehouse_id.partner_id,
                'picking_warehouse_partner_phone': self._convert_phone_number(picking.picking_type_id.warehouse_id.partner_id.phone),
                'picking_partner': picking.partner_id,
                'picking_partner_phone': self._convert_phone_number(picking.partner_id.phone or picking.partner_id.mobile or ''),
            })
        else:
            shipping_detail.update({
                'picking_warehouse_partner': picking.partner_id,
                'picking_warehouse_partner_phone': self._convert_phone_number(picking.partner_id.phone or picking.partner_id.mobile or ''),
                'picking_partner': picking.picking_type_id.warehouse_id.partner_id,
                'picking_partner_phone': self._convert_phone_number(picking.picking_type_id.warehouse_id.partner_id.phone),
            })

        return shipping_detail

    def usps_request(self, picking, delivery_nature, service, is_return=False):
        ship_detail = self._usps_shipping_data(picking, is_return)
        request_text = picking.env['ir.qweb']._render('delivery_usps.usps_shipping_common', ship_detail)
        api = self._api_url(delivery_nature, service)
        dict_response = {'tracking_number': 0.0, 'price': 0.0, 'currency': "USD"}
        try:
            self.debug_logger(request_text, 'usps_request_ship')
            req = requests.get(self.url, params={'API': api, 'XML': request_text})
            req.raise_for_status()
            response_text = req.content
            self.debug_logger(response_text, 'usps_response_ship')
        except IOError:
            dict_response['error_message'] = 'USPS Server Not Found - Check your connectivity'

        root = etree.fromstring(response_text)
        errors_return = root.findall('.//Description')
        errors_number = root.findall('.//Number')

        if errors_return:
            dict_response['error_message'] = self._error_message(errors_number[0].text, errors_return[0].text)
            return dict_response
        else:
            dict_response['tracking_number'] = root.findtext('BarcodeNumber')
            dict_response['price'] = float(root.findtext('Postage'))
            dict_response['label'] = binascii.a2b_base64(root.findtext('LabelImage'))

        return dict_response

    def _usps_cancel_shipping_data(self, picking):
        return {
            'ID': picking.carrier_id.sudo().usps_username,
            'BarcodeNumber': picking.carrier_tracking_ref,
            'carrier_type': picking.carrier_id.usps_delivery_nature,
            'api': 'eVSCancel' if self.prod_environment else 'eVSCancelCertify'
        }

    def cancel_shipment(self, picking, account_validated):
        cancel_detail = self._usps_cancel_shipping_data(picking)
        request_text = picking.env["ir.qweb"]._render('delivery_usps.usps_cancel_request', cancel_detail)
        dict_response = {'ShipmentDeleted': False, 'error_found': False}
        # If the account isn't validated by USPS you can't use cancelling methods. It returns an authentication error.
        if not account_validated:
            dict_response['ShipmentDeleted'] = True
        else:
            api = 'eVSCancel' if self.prod_environment else 'eVSCancelCertify'
            try:
                self.debug_logger(request_text, 'usps_request_cancel')
                req = requests.get(self.url, params={'API': api, 'XML': request_text})
                req.raise_for_status()
                response_text = req.content
                self.debug_logger(response_text, 'usps_response_cancel')
            except IOError:
                dict_response['error_message'] = 'USPS Server Not Found - Check your connectivity'
            root = etree.fromstring(response_text)
            errors_return = root.findall('.//Description')
            if errors_return:
                dict_response['error_message'] = errors_return[0].text
                dict_response['error_found'] = True
                return dict_response
            else:
                dict_response['ShipmentDeleted'] = True
        return dict_response

    def _api_url(self, delivery_nature, service):
        api = ''
        if not self.prod_environment:
            if delivery_nature == 'domestic':
                api = 'eVSCertify'
            else:
                api = "eVS%s%s" % (str(service).replace(" ", ""), 'MailIntlCertify')
        else:
            if delivery_nature == 'domestic':
                api = 'eVS'
            else:
                api = "eVS%s%s" % (str(service).replace(" ", ""), 'MailIntl')
        return api

    def _convert_phone_number(self, phone):
        phone_pattern = re.compile(r'''
                # don't match beginning of string, number can start anywhere
                (\d{3})     # area code is 3 digits (e.g. '800')
                \D*         # optional separator is any number of non-digits
                (\d{3})     # trunk is 3 digits (e.g. '555')
                \D*         # optional separator
                (\d{4})     # rest of number is 4 digits (e.g. '1212')
                \D*         # optional separator
                (\d*)       # extension is optional and can be any number of digits
                $           # end of string
                ''', re.VERBOSE)
        match = phone_pattern.search(phone)
        if match:
            return ''.join(str(digits_number) for digits_number in match.groups())
        else:
            return False

    def _error_message(self, error_number, api_error_message):
        if error_number == '-2147219401':
            api_error_message += _("Recipient address cannot be found. Please check the address exists.")
        elif error_number == '-2147219385':
            api_error_message += _("Your company or recipient ZIP code is incorrect.")
        return api_error_message
