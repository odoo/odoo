# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from binascii import a2b_base64
import io
import logging
import re
import requests
from lxml import html
from PyPDF2 import PdfFileWriter, PdfFileReader
from xml.etree import ElementTree as etree
from werkzeug.urls import url_join

from odoo import _
from odoo.exceptions import UserError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


COUNTRIES_WITHOUT_POSTCODES = [
    'AO', 'AG', 'AW', 'BS', 'BZ', 'BJ', 'BW', 'BF', 'BI', 'CM', 'CF', 'KM',
    'CG', 'CD', 'CK', 'CI', 'DJ', 'DM', 'GQ', 'ER', 'FJ', 'TF', 'GM', 'GH',
    'GD', 'GN', 'GY', 'HK', 'IE', 'JM', 'KE', 'KI', 'MO', 'MW', 'ML', 'MR',
    'MU', 'MS', 'NR', 'AN', 'NU', 'KP', 'PA', 'QA', 'RW', 'KN', 'LC', 'ST',
    'SC', 'SL', 'SB', 'SO', 'ZA', 'SR', 'SY', 'TZ', 'TL', 'TK', 'TO', 'TT',
    'TV', 'UG', 'AE', 'VU', 'YE', 'ZW'
]

def _grams(kilograms):
    return int(kilograms * 1000)


class BpostRequest():

    def __init__(self, prod_environment, debug_logger):
        self.debug_logger = debug_logger
        if prod_environment:
            self.base_url = 'https://api-parcel.bpost.be/services/shm/'
        else:
            self.base_url = 'https://api-parcel.bpost.be/services/shm/'

    def check_required_value(self, recipient, delivery_nature, shipper, order=False, picking=False):
        recipient_required_fields = ['city', 'country_id']
        if recipient.country_id.code not in COUNTRIES_WITHOUT_POSTCODES:
            recipient_required_fields.append('zip')
        # The street isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not recipient.street and not recipient.street2 and not recipient._context.get(
            'express_checkout_partial_delivery_address', False
        ):
            recipient_required_fields.append('street')
        shipper_required_fields = ['city', 'zip', 'country_id']
        if not shipper.street and not shipper.street2:
            shipper_required_fields.append('street')

        res = [field for field in recipient_required_fields if not recipient[field]]
        if res:
            return _("The recipient address is incomplete or wrong (Missing field(s):  \n %s)", ", ".join(res).replace("_id", ""))
        if recipient.country_id.code == "BE" and delivery_nature == 'International':
            return _("bpost International is used only to ship outside Belgium. Please change the delivery method into bpost Domestic.")
        if recipient.country_id.code != "BE" and delivery_nature == 'Domestic':
            return _("bpost Domestic is used only to ship inside Belgium. Please change the delivery method into bpost International.")

        res = [field for field in shipper_required_fields if not shipper[field]]
        if res:
            return _("The address of your company/warehouse is incomplete or wrong (Missing field(s):  \n %s)", ", ".join(res).replace("_id", ""))
        if shipper.country_id.code != 'BE':
            return _("Your company/warehouse address must be in Belgium to ship with bpost")

        if order:
            if order.order_line and all(order.order_line.mapped(lambda l: l.product_id.type == 'service')):
                return _("The estimated shipping price cannot be computed because all your products are service.")
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            error_lines = order.order_line.filtered(lambda line: not line.product_id.weight and not line.is_delivery and line.product_id.type != 'service' and not line.display_type)
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s", ", ".join(error_lines.product_id.mapped('name')))
        return False

    def _parse_address(self, partner):
        if partner.street and partner.street2:
            street = '%s %s' % (partner.street, partner.street2)
        else:
            street = partner.street or partner.street2
        match = re.match(r'^(.*?)(\S*\d+\S*)?\s*$', street, re.DOTALL)
        street = match.group(1)
        street_number = match.group(2)  # None if no number found
        if street_number and len(street_number) > 8:
            street = match.group(0)
            street_number = None
        return (street, street_number)

    def rate(self, order, carrier):
        weight_in_kg = carrier._bpost_convert_weight(order._get_estimated_weight())
        return self._get_rate(carrier, _grams(weight_in_kg), order.partner_shipping_id.country_id)

    def _get_rate(self, carrier, weight, country):
        '''@param carrier: a record of the delivery.carrier
           @param weight: in grams
           @param country: a record of the destination res.country'''

        # Surprisingly, bpost does not require to send other data while asking for prices;
        # they simply return a price grid for all activated products for this account.
        code, response = self._send_request('rate', None, carrier)
        if code == 401 and response:
            # If the authentication fails, the server returns plain HTML instead of XML
            error_page = html.fromstring(response)
            error_message = error_page.body.text_content()
            raise UserError(_("Authentication error -- wrong credentials\n(Detailed error: %s)", error_message))
        else:
            xml_response = etree.fromstring(response)

        # Find price by product and country
        price = 0.0
        ns = {'ns1': 'http://schema.post.be/shm/deepintegration/v3/'}
        bpost_delivery_type = carrier.bpost_domestic_deliver_type if carrier.bpost_delivery_nature == 'Domestic' else carrier.bpost_international_deliver_type
        for delivery_method in xml_response.findall('ns1:deliveryMethod/[@name="home or office"]/ns1:product/[@name="%s"]/ns1:price' % bpost_delivery_type, ns):
            if delivery_method.attrib['countryIso2Code'] == country.code:
                price = float(self._get_price_by_weight(weight, delivery_method))/100
                sale_price_digits = carrier.env['decimal.precision'].precision_get('Product Price')
                price = float_round(price, precision_digits=sale_price_digits)
        if not price:
            raise UserError(_("bpost did not return prices for this destination country."))

        # If delivery on saturday is enabled, there are additional fees
        additional_fees = 0.0
        if carrier.bpost_saturday is True:
            for option_price in xml_response.findall('ns1:deliveryMethod/[@name="home or office"]/ns1:product/[@name="%s"]/ns1:option/[@name="Saturday"]' % bpost_delivery_type, ns):
                additional_fees = float(option_price.attrib['price'])

        return price + additional_fees

    def _get_price_by_weight(self, weight, price):
        if weight <= 2000:
            return price.attrib['priceLessThan2']
        elif weight <= 5000:
            return price.attrib['price2To5']
        elif weight <= 10000:
            return price.attrib['price5To10']
        elif weight <= 20000:
            return price.attrib['price10To20']
        elif weight <= 30000:
            return price.attrib['price20To30']
        else:
            raise UserError(_("Packages over 30 Kg are not accepted by bpost."))

    def send_shipping(self, picking, carrier, with_return_label, is_return_label=False):

        if is_return_label:
            receiver = picking.picking_type_id.warehouse_id.partner_id
            receiver_company = ''
            sender = picking.partner_id
            boxes = self._compute_return_boxes(picking, carrier)
        else:
            receiver = picking.partner_id
            receiver_company = receiver.commercial_partner_id.name if receiver.commercial_partner_id != receiver else ''
            sender = picking.picking_type_id.warehouse_id.partner_id
            boxes = self._compute_boxes(picking, carrier)

        ###### need to change the get_rate !!!!!!!!!!
        price = 0.0
        for box in boxes:
            price += self._get_rate(carrier, int(box['weight']), picking.partner_id.country_id)

        # Announce shipment to bpost
        reference_id = str(picking.name.replace("/", ""))[:50]
        ss, sn = self._parse_address(sender)
        rs, rn = self._parse_address(receiver)

        # bpsot only allow a zip with a size of 8 characters. In some country
        # (e.g. brazil) the postalCode could be longer than 8. In this case we
        # set the zip in the locality.
        receiver_postal_code = receiver.zip
        receiver_locality = receiver.city

        # Some country do not use zip code (Saudi Arabia, Congo, ...). Bpost
        # always require at least a zip or a PO box.
        if not receiver_postal_code:
            receiver_postal_code = '/'
        elif len(receiver_postal_code) > 8:
            receiver_locality = '%s %s' % (receiver_locality, receiver_postal_code)
            receiver_postal_code = '/'

        if receiver.state_id:
            receiver_locality = '%s, %s' % (receiver_locality, picking.partner_id.state_id.display_name)

        values = {'accountId': carrier.sudo().bpost_account_number,
                  'reference': reference_id,
                  'sender': {'_record': sender,
                             'streetName': ss,
                             'number': sn,
                             },
                  'receiver': {'_record': receiver,
                               'company': receiver_company,
                               'streetName': rs,
                               'number': rn,
                               'locality': receiver_locality,
                               'postalCode': receiver_postal_code,
                               },
                  'is_domestic': carrier.bpost_delivery_nature == 'Domestic',
                  # domestic
                  'product': 'bpack Easy Retour' if is_return_label else carrier.bpost_domestic_deliver_type,
                  'saturday': carrier.bpost_saturday,
                  # international
                  'international_product': carrier.bpost_international_deliver_type,
                  'shipmentType': carrier.bpost_shipment_type,
                  'parcelReturnInstructions': carrier.bpost_parcel_return_instructions,
                  'boxes': boxes,
                  '_record': picking,
                  }
        xml = carrier.env['ir.qweb']._render('delivery_bpost.bpost_shipping_request', values)
        code, response = self._send_request('send', xml.encode(), carrier)
        if code != 201 and response:
            try:
                root = etree.fromstring(response)
                ns = {'ns1': 'http://schema.post.be/shm/deepintegration/v3/'}
                for errors_return in root.findall("ns1:error", ns):
                    raise UserError(errors_return.text)
            except etree.ParseError:
                    raise UserError(response)

        # Grab printable label and tracking code
        code, response2 = self._send_request('label', None, carrier, reference=reference_id, with_return_label=with_return_label)
        root = etree.fromstring(response2)
        ns = {'ns1': 'http://schema.post.be/shm/deepintegration/v3/'}
        for labels in root.findall('ns1:label', ns):
            if with_return_label:
                main_label, return_label = self._split_labels(labels, ns)
            else:
                main_label = {
                    'tracking_codes': [label.text for label in labels.findall("ns1:barcode", ns)],
                    'label': a2b_base64(labels.find("ns1:bytes", ns).text)
                }
                return_label = False
        return {
            'price': price,
            'main_label': main_label,
            'return_label': return_label
        }

    def _split_labels(self, labels, ns):

        def _get_page(src_pdf, page_nums):
            with io.BytesIO(base64.b64decode(src_pdf)) as stream:
                try:
                    pdf = PdfFileReader(stream)
                    writer = PdfFileWriter()
                    for page in page_nums:
                        writer.addPage(pdf.getPage(page))
                    stream2 = io.BytesIO()
                    writer.write(stream2)
                    return a2b_base64(base64.b64encode(stream2.getvalue()))
                except Exception:
                    _logger.error('Error ')
                    return False

        barcodes = labels.findall("ns1:barcode", ns)
        src_pdf = labels.find("ns1:bytes", ns).text

        # return barcodes ends with '050'
        main_indeces = [index for index, barcode in enumerate(barcodes) if barcode.text[-3:] != '050']
        return_indeces = [index for index, barcode in enumerate(barcodes) if barcode.text[-3:] == '050']

        main_label = {
            'tracking_codes': [barcodes[index].text for index in main_indeces],
            'label': _get_page(src_pdf, main_indeces)
        }

        return_label = False
        if len(barcodes) > 1:
            return_label = {
                'tracking_codes': [barcodes[index].text for index in return_indeces],
                'label': _get_page(src_pdf, return_indeces)
            }

        return (main_label, return_label)

    def _send_request(self, action, xml, carrier, reference=None, with_return_label=False):
        supercarrier = carrier.sudo()
        passphrase = supercarrier._bpost_passphrase()
        METHODS = {'rate': 'GET',
                   'send': 'POST',
                   'label': 'GET'}
        HEADERS = {'rate': {'authorization': 'Basic %s' % passphrase,
                            'accept': 'application/vnd.bpost.shm-productConfiguration-v3.1+XML'},
                   'send': {'authorization': 'Basic %s' % passphrase,
                            'content-Type': 'application/vnd.bpost.shm-order-v3.3+XML'},
                   'label': {'authorization': 'Basic %s' % passphrase,
                             'accept': 'application/vnd.bpost.shm-label-%s-v3+XML' % ('pdf' if carrier.bpost_label_format == 'PDF' else 'image'),
                             'content-Type': 'application/vnd.bpost.shm-labelRequest-v3+XML'}}
        label_url = url_join(self.base_url, '%s/orders/%s/labels/%s' % (supercarrier.bpost_account_number, reference, carrier.bpost_label_stock_type))
        if with_return_label:
            label_url += '/withReturnLabels'
        URLS = {'rate': url_join(self.base_url, '%s/productconfig' % supercarrier.bpost_account_number),
                'send': url_join(self.base_url, '%s/orders' % supercarrier.bpost_account_number),
                'label': label_url}
        self.debug_logger("%s\n%s\n%s" % (URLS[action], HEADERS[action], xml if xml else None), 'bpost_request_%s' % action)
        try:
            response = requests.request(METHODS[action], URLS[action], headers=HEADERS[action], data=xml, timeout=15)
        except requests.exceptions.Timeout:
            raise UserError(_('The BPost shipping service is unresponsive, please retry later.'))
        self.debug_logger("%s\n%s" % (response.status_code, response.text), 'bpost_response_%s' % action)

        return response.status_code, response.text

    def _compute_boxes(self, picking, carrier):
        """Group the move lines in the picking to different boxes.

        Lines with the same result_package_id belong to the same box,
        and lines without result_package_id are assigned to one box.
        This method returns a list of summary of each box which will be
        used in creating the request in making order in bpost.
        """
        boxes = []
        for package in picking.package_ids:
            package_lines = picking.move_line_ids.filtered(lambda sml: sml.result_package_id.id == package.id)
            parcel_value = sum(sml.sale_price for sml in package_lines)
            weight_in_kg = carrier._bpost_convert_weight(package.shipping_weight)
            boxes.append({
                'weight': str(_grams(weight_in_kg)),
                'parcelValue': max(min(int(parcel_value * 100), 2500000), 100),
                'contentDescription': ' '.join(["%d %s" % (line.quantity, re.sub(r'[\W_]+', ' ', line.product_id.name or '')) for line in package_lines])[:50],
            })
        lines_without_package = picking.move_line_ids.filtered(lambda sml: not sml.result_package_id)
        if lines_without_package:
            parcel_value = sum(sml.sale_price for sml in lines_without_package)
            weight_in_kg = carrier._bpost_convert_weight(sum(sml.quantity * sml.product_id.weight for sml in lines_without_package))
            boxes.append({
                'weight': str(_grams(weight_in_kg)),
                'parcelValue': max(min(int(parcel_value * 100), 2500000), 100),
                'contentDescription': ' '.join(["%d %s" % (line.quantity, re.sub(r'[\W_]+', ' ', line.product_id.name or '')) for line in lines_without_package])[:50],
            })
        return boxes

    def _compute_return_boxes(self, picking, carrier):
        weight = sum(move.product_qty * move.product_id.weight for move in picking.move_ids)
        weight_in_kg = carrier._bpost_convert_weight(weight)
        parcel_value = sum(move.product_qty * move.product_id.lst_price for move in picking.move_ids)
        boxes = [{
            'weight': str(_grams(weight_in_kg)),
            'parcelValue': max(min(int(parcel_value * 100), 2500000), 100),
            'contentDescription': ' '.join(["%d %s" % (line.product_qty, re.sub(r'[\W_]+', ' ', line.product_id.name or '')) for line in picking.move_ids])[:50],
        }]
        return boxes
