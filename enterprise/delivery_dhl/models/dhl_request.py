# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from lxml.etree import fromstring
from datetime import datetime, date, timedelta
from lxml import etree
from odoo.tools.zeep import Client, Plugin
from odoo.tools.zeep.wsdl.utils import etree_to_string

from odoo import _
from odoo import release
from odoo.exceptions import UserError
from odoo.tools import float_repr, float_round
from odoo.tools.misc import file_path

class DHLProvider():

    def __init__(self, debug_logger, request_type='ship', prod_environment=False):
        self.debug_logger = debug_logger
        if not prod_environment:
            self.url = 'https://xmlpitest-ea.dhl.com/XMLShippingServlet?isUTF8Support=true'
        else:
            self.url = 'https://xmlpi-ea.dhl.com/XMLShippingServlet?isUTF8Support=true'
        if request_type == "ship":
            self.client = self._set_client('ship-10.0.wsdl', 'Ship')
            self.factory = self.client.type_factory('ns1')
        elif request_type =="rate":
            self.client = self._set_client('rate.wsdl', 'Rate')
            self.factory = self.client.type_factory('ns1')
            self.factory_dct_request = self.client.type_factory('ns2')
            self.factory_dct_response = self.client.type_factory('ns3')


    def _set_client(self, wsdl_filename, api):
        wsdl_path = file_path(f'delivery_dhl/api/{wsdl_filename}')
        client = Client(wsdl_path)
        return client

    def _set_request(self, site_id, password):
        request = self.factory.Request()
        service_header = self.factory.ServiceHeader()
        service_header.MessageTime = datetime.now()
        service_header.MessageReference = 'ref:' + datetime.now().isoformat() #CHANGEME
        service_header.SiteID = site_id
        service_header.Password = password
        request.ServiceHeader = service_header
        metadata = self.factory.MetaData()
        metadata.SoftwareName = release.product_name
        metadata.SoftwareVersion = release.series
        request.MetaData = metadata
        return request

    def _set_region_code(self, region_code):
        return region_code

    def _set_requested_pickup_time(self, requested_pickup):
        if requested_pickup:
            return "Y"
        else:
            return "N"

    def _set_billing(self, shipper_account, payment_type, duty_payment_type, is_dutiable):
        billing = self.factory.Billing()
        billing.ShipperAccountNumber = shipper_account
        billing.ShippingPaymentType = payment_type
        if is_dutiable:
            billing.DutyPaymentType = duty_payment_type
        return billing

    def _set_consignee(self, partner_id):
        consignee = self.factory.Consignee()
        consignee.CompanyName = partner_id.commercial_company_name or partner_id.name
        consignee.AddressLine1 = partner_id.street or partner_id.street2
        consignee.AddressLine2 = partner_id.street and partner_id.street2 or None
        consignee.City = partner_id.city
        if partner_id.state_id:
            consignee.Division = partner_id.state_id.name
            consignee.DivisionCode = partner_id.state_id.code
        consignee.PostalCode = partner_id.zip
        consignee.CountryCode = partner_id.country_id.code
        consignee.CountryName = partner_id.country_id.name
        contact = self.factory.Contact()
        contact.PersonName = partner_id.name
        contact.PhoneNumber = partner_id.phone
        if partner_id.email:
            contact.Email = partner_id.email
        consignee.Contact = contact
        return consignee

    def _set_dct_to(self, partner_id):
        to = self.factory_dct_request.DCTTo()
        country_code = partner_id.country_id.code
        zip_code = partner_id.zip or ''
        if country_code == 'ES' and (zip_code.startswith('35') or zip_code.startswith('38')):
            country_code = 'IC'
        to.CountryCode = country_code
        to.Postalcode = zip_code
        to.City = partner_id.city
        return to

    def _set_shipper(self, account_number, company_partner_id, warehouse_partner_id):
        shipper = self.factory.Shipper()
        shipper.ShipperID = account_number
        shipper.CompanyName = company_partner_id.name
        shipper.AddressLine1 = warehouse_partner_id.street or warehouse_partner_id.street2
        shipper.AddressLine2 = warehouse_partner_id.street and warehouse_partner_id.street2 or None
        shipper.City = warehouse_partner_id.city
        if warehouse_partner_id.state_id:
            shipper.Division = warehouse_partner_id.state_id.name
            shipper.DivisionCode = warehouse_partner_id.state_id.code
        shipper.PostalCode = warehouse_partner_id.zip
        shipper.CountryCode = warehouse_partner_id.country_id.code
        shipper.CountryName = warehouse_partner_id.country_id.name
        contact = self.factory.Contact()
        contact.PersonName = warehouse_partner_id.name
        contact.PhoneNumber = warehouse_partner_id.phone
        if warehouse_partner_id.email:
            contact.Email = warehouse_partner_id.email
        shipper.Contact = contact
        return shipper

    def _set_dct_from(self, warehouse_partner_id):
        dct_from = self.factory_dct_request.DCTFrom()
        dct_from.CountryCode = warehouse_partner_id.country_id.code
        dct_from.Postalcode = warehouse_partner_id.zip
        dct_from.City = warehouse_partner_id.city
        return dct_from

    def _set_dutiable(self, total_value, currency_name, incoterm):
        dutiable = self.factory.Dutiable()
        dutiable.DeclaredValue = float_repr(total_value, 2)
        dutiable.DeclaredCurrency = currency_name
        if not incoterm:
            raise UserError(_("Please define an incoterm in the associated sale order or set a default incoterm for the company in the accounting's settings."))
        dutiable.TermsOfTrade = incoterm.code
        return dutiable

    def _set_dct_dutiable(self, total_value, currency_name):
        dct_dutiable = self.factory_dct_request.DCTDutiable()
        dct_dutiable.DeclaredCurrency = currency_name
        dct_dutiable.DeclaredValue = total_value
        return dct_dutiable

    def _set_dct_bkg_details(self, carrier, packages):
        bkg_details = self.factory_dct_request.BkgDetailsType()
        bkg_details.PaymentCountryCode = packages[0].company_id.partner_id.country_id.code
        bkg_details.Date = date.today()
        bkg_details.ReadyTime = timedelta(hours=1,minutes=2)
        bkg_details.DimensionUnit = "CM" if carrier.dhl_package_dimension_unit == "C" else "IN"
        bkg_details.WeightUnit = "KG" if carrier.dhl_package_weight_unit == "K" else "LB"
        bkg_details.InsuredValue = float_repr(sum(pkg.total_cost for pkg in packages) * carrier.shipping_insurance / 100, precision_digits=3)
        bkg_details.InsuredCurrency = packages[0].currency_id.name
        pieces = []
        for sequence, package in enumerate(packages):
            piece = self.factory_dct_request.PieceType()
            piece.PieceID = sequence
            piece.PackageTypeCode = package.packaging_type
            piece.Height = package.dimension['height']
            piece.Depth = package.dimension['length']
            piece.Width = package.dimension['width']
            piece.Weight = carrier._dhl_convert_weight(package.weight, carrier.dhl_package_weight_unit)
            pieces.append(piece)
        bkg_details.Pieces = {'Piece': pieces}
        bkg_details.PaymentAccountNumber = carrier.dhl_account_number
        if carrier.dhl_dutiable:
            bkg_details.IsDutiable = "Y"
        else:
            bkg_details.IsDutiable = "N"
        bkg_details.NetworkTypeCode = "AL"
        return bkg_details

    def _set_shipment_details(self, picking):
        shipment_details = self.factory.ShipmentDetails()
        pieces = []
        packages = picking.carrier_id._get_packages_from_picking(picking, picking.carrier_id.dhl_default_package_type_id)
        for sequence, package in enumerate(packages):
            piece = self.factory.Piece()
            piece.PieceID = sequence
            piece.Height = package.dimension['height']
            piece.Depth = package.dimension['length']
            piece.Width = package.dimension['width']
            piece.Weight = picking.carrier_id._dhl_convert_weight(package.weight, picking.carrier_id.dhl_package_weight_unit)
            piece.PieceContents = package.name
            pieces.append(piece)
        shipment_details.Pieces = self.factory.Pieces(pieces)
        shipment_details.WeightUnit = picking.carrier_id.dhl_package_weight_unit
        shipment_details.GlobalProductCode = picking.carrier_id.dhl_product_code
        shipment_details.LocalProductCode = picking.carrier_id.dhl_product_code
        shipment_details.Date = date.today()
        shipment_details.Contents = "MY DESCRIPTION"
        shipment_details.DimensionUnit = picking.carrier_id.dhl_package_dimension_unit
        shipment_details.InsuredAmount = float_repr(sum(pkg.total_cost for pkg in packages) * picking.carrier_id.shipping_insurance / 100, precision_digits=2)
        if picking.carrier_id.dhl_dutiable:
            shipment_details.IsDutiable = "Y"
        currency = picking.group_id.sale_id.currency_id or picking.company_id.currency_id
        shipment_details.CurrencyCode = currency.name
        return shipment_details

    def _set_label_image_format(self, label_image_format):
        return label_image_format

    def _set_label(self, label):
        label_obj = self.factory.Label()
        label_obj.LabelTemplate = label
        return label_obj

    def _set_return(self):
        return_service = self.factory.SpecialService()
        return_service.SpecialServiceType = "PV"
        return return_service

    def _set_insurance(self, shipment_details):
        insurance_service = self.factory.SpecialService()
        insurance_service.SpecialServiceType = "II"
        insurance_service.ChargeValue = shipment_details.InsuredAmount
        insurance_service.CurrencyCode = shipment_details.CurrencyCode
        return insurance_service

    def _process_shipment(self, shipment_request):
        ShipmentRequest  = self.client._Client__obj.get_element('ns0:ShipmentRequest')
        document = etree.Element('root')
        ShipmentRequest.render(document, shipment_request)
        request_to_send = etree_to_string(list(document)[0])
        headers = {'Content-Type': 'text/xml'}
        response = self.client._Client__obj.transport.post(self.url, request_to_send, headers=headers)
        if self.debug_logger:
            self.debug_logger(request_to_send, 'dhl_shipment_request')
            self.debug_logger(response.content, 'dhl_shipment_response')
        response_element_xml = fromstring(response.content)
        Response = self.client._Client__obj.get_element(response_element_xml.tag)
        response_zeep = Response.type.parse_xmlelement(response_element_xml)
        dict_response = {'tracking_number': 0.0,
                         'price': 0.0,
                         'currency': False}
        # This condition handle both 'ShipmentValidateErrorResponse' and
        # 'ErrorResponse', we could handle them differently if needed as
        # the 'ShipmentValidateErrorResponse' is something you cannot do,
        # and 'ErrorResponse' are bad values given in the request.
        if hasattr(response_zeep.Response, 'Status'):
            condition = response_zeep.Response.Status.Condition[0]
            error_msg = "%s: %s" % (condition.ConditionCode, condition.ConditionData)
            raise UserError(error_msg)
        return response_zeep

    def _process_rating(self, rating_request):
        DCTRequest  = self.client._Client__obj.get_element('ns0:DCTRequest')
        document = etree.Element('root')
        DCTRequest.render(document, rating_request)
        request_to_send = etree_to_string(list(document)[0])
        headers = {'Content-Type': 'text/xml'}
        response = self.client._Client__obj.transport.post(self.url, request_to_send, headers=headers)
        if self.debug_logger:
            self.debug_logger(request_to_send, 'dhl_rating_request')
            self.debug_logger(response.content, 'dhl_rating_response')
        response_element_xml = fromstring(response.content)
        dict_response = {'tracking_number': 0.0,
                         'price': 0.0,
                         'currency': False}
        # This condition handle both 'ShipmentValidateErrorResponse' and
        # 'ErrorResponse', we could handle them differently if needed as
        # the 'ShipmentValidateErrorResponse' is something you cannot do,
        # and 'ErrorResponse' are bad values given in the request.
        if response_element_xml.find('GetQuoteResponse') is not None:
            return response_element_xml
        else:
            condition = response_element_xml.find('Response/Status/Condition')
            error_msg = "%s: %s" % (condition.find('ConditionCode').text, condition.find('ConditionData').text)
            raise UserError(error_msg)

    def check_required_value(self, carrier, recipient, shipper, order=False, picking=False):
        carrier = carrier.sudo()
        recipient_required_field = ['city', 'zip', 'country_id']
        if not carrier.dhl_SiteID:
            return _("DHL Site ID is missing, please modify your delivery method settings.")
        if not carrier.dhl_password:
            return _("DHL password is missing, please modify your delivery method settings.")
        if not carrier.dhl_account_number:
            return _("DHL account number is missing, please modify your delivery method settings.")

        # The street isn't required if we compute the rate with a partial delivery address in the
        # express checkout flow.
        if not recipient.street and not recipient.street2 and not recipient._context.get(
            'express_checkout_partial_delivery_address', False
        ):
            recipient_required_field.append('street')
        res = [field for field in recipient_required_field if not recipient[field]]
        if res:
            return _("The address of the customer is missing or wrong (Missing field(s) :\n %s)", ", ".join(res).replace("_id", ""))

        shipper_required_field = ['city', 'zip', 'phone', 'country_id']
        if not shipper.street and not shipper.street2:
            shipper_required_field.append('street')

        res = [field for field in shipper_required_field if not shipper[field]]
        if res:
            return _("The address of your company warehouse is missing or wrong (Missing field(s) :\n %s)", ", ".join(res).replace("_id", ""))

        if order:
            if not order.order_line:
                return _("Please provide at least one item to ship.")
            error_lines = order.order_line._get_invalid_delivery_weight_lines()
            if error_lines:
                return _("The estimated shipping price cannot be computed because the weight is missing for the following product(s): \n %s", ", ".join(error_lines.product_id.mapped('name')))
        return False

    def _set_export_declaration(self, carrier, picking, is_return=False):
        export_lines = []
        move_lines = picking.move_line_ids.filtered(lambda line: line.product_id.type == 'consu')
        currency_id = picking.sale_id and picking.sale_id.currency_id or picking.company_id.currency_id
        for sequence, line in enumerate(move_lines, start=1):
            if line.move_id.sale_line_id:
                unit_quantity = line.product_uom_id._compute_quantity(line.quantity, line.move_id.sale_line_id.product_uom)
            else:
                unit_quantity = line.product_uom_id._compute_quantity(line.quantity, line.product_id.uom_id)
            rounded_qty = max(1, float_round(unit_quantity, precision_digits=0, rounding_method='HALF-UP'))
            item = self.factory.ExportLineItem()
            item.LineNumber = sequence
            item.Quantity = int(rounded_qty)
            item.QuantityUnit = 'PCS'  # Pieces - very generic
            if len(line.product_id.name) > 75:
                raise UserError(_("DHL doesn't support products with name greater than 75 characters."))
            item.Description = line.product_id.name
            item.Value = float_repr(line.sale_price / rounded_qty, currency_id.decimal_places)
            item.Weight = item.GrossWeight = {
                "Weight": carrier._dhl_convert_weight(line.product_id.weight, carrier.dhl_package_weight_unit),
                "WeightUnit": carrier.dhl_package_weight_unit,
            }
            item.ManufactureCountryCode = line.product_id.country_of_origin.code or line.picking_id.picking_type_id.warehouse_id.partner_id.country_id.code
            if line.product_id.hs_code:
                item.ImportCommodityCode = line.product_id.hs_code
                item.CommodityCode = line.product_id.hs_code
            export_lines.append(item)

        export_declaration = self.factory.ExportDeclaration()
        export_declaration.InvoiceDate = datetime.today()
        export_declaration.InvoiceNumber = carrier.env['ir.sequence'].sudo().next_by_code('delivery_dhl.commercial_invoice')
        if is_return:
            export_declaration.ExportReason = 'RETURN'

        export_declaration.ExportLineItem = export_lines
        if picking.sale_id.client_order_ref:
            export_declaration.ReceiverReference = picking.sale_id.client_order_ref
        return export_declaration
