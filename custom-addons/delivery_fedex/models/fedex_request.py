# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import binascii
import logging
import re

from datetime import datetime, date
from os.path import join as opj
from odoo.tools.zeep import Client, Plugin, Settings
from odoo.tools.zeep.exceptions import Fault
from odoo.tools.zeep.wsdl.utils import etree_to_string

from odoo.tools import remove_accents, float_repr
from odoo.tools.misc import file_path


_logger = logging.getLogger(__name__)
# uncomment to enable logging of Zeep requests and responses
# logging.getLogger('zeep.transports').setLevel(logging.DEBUG)


STATECODE_REQUIRED_COUNTRIES = ['US', 'CA', 'PR ', 'IN']

# Why using standardized ISO codes? It's way more fun to use made up codes...
# https://www.fedex.com/us/developer/WebHelp/ws/2014/dvg/WS_DVG_WebHelp/Appendix_F_Currency_Codes.htm
FEDEX_CURR_MATCH = {
    u'UYU': u'UYP',
    u'XCD': u'ECD',
    u'MXN': u'NMP',
    u'KYD': u'CID',
    u'CHF': u'SFR',
    u'GBP': u'UKL',
    u'IDR': u'RPA',
    u'DOP': u'RDD',
    u'JPY': u'JYE',
    u'KRW': u'WON',
    u'SGD': u'SID',
    u'CLP': u'CHP',
    u'JMD': u'JAD',
    u'KWD': u'KUD',
    u'AED': u'DHS',
    u'TWD': u'NTD',
    u'ARS': u'ARN',
    u'LVL': u'EURO',
}

class LogPlugin(Plugin):
    """ Small plugin for zeep that catches out/ingoing XML requests and logs them"""
    def __init__(self, debug_logger):
        self.debug_logger = debug_logger

    def egress(self, envelope, http_headers, operation, binding_options):
        self.debug_logger(etree_to_string(envelope).decode(), 'fedex_request')
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        self.debug_logger(etree_to_string(envelope).decode(), 'fedex_response')
        return envelope, http_headers

    def marshalled(self, context):
        context.envelope = context.envelope.prune()


class FedexRequest():
    """ Low-level object intended to interface Odoo recordsets with FedEx,
        through appropriate SOAP requests """

    def __init__(self, debug_logger, request_type="shipping", prod_environment=False, ):
        self.debug_logger = debug_logger
        self.hasCommodities = False

        wsdl_folder = 'prod' if prod_environment else 'test'
        if request_type == "shipping":
            wsdl_path = opj('delivery_fedex', 'api', wsdl_folder, 'ShipService_v28.wsdl')
            self.start_shipping_transaction(wsdl_path)
        elif request_type == "rating":
            wsdl_path = opj('delivery_fedex', 'api', wsdl_folder, 'RateService_v31.wsdl')
            self.start_rating_transaction(wsdl_path)

    # Authentification stuff

    def web_authentication_detail(self, key, password):
        WebAuthenticationCredential = self.factory.WebAuthenticationCredential()
        WebAuthenticationCredential.Key = key
        WebAuthenticationCredential.Password = password
        self.WebAuthenticationDetail = self.factory.WebAuthenticationDetail()
        self.WebAuthenticationDetail.UserCredential = WebAuthenticationCredential

    def transaction_detail(self, transaction_id):
        self.TransactionDetail = self.factory.TransactionDetail()
        self.TransactionDetail.CustomerTransactionId = transaction_id

    def client_detail(self, account_number, meter_number):
        self.ClientDetail = self.factory.ClientDetail()
        self.ClientDetail.AccountNumber = account_number
        self.ClientDetail.MeterNumber = meter_number

    # Common stuff

    def set_shipper(self, company_partner, warehouse_partner):
        Contact = self.factory.Contact()
        Contact.PersonName = remove_accents(company_partner.name) if not company_partner.is_company else ''
        Contact.CompanyName = remove_accents(company_partner.commercial_company_name) or ''
        Contact.PhoneNumber = warehouse_partner.phone or ''
        Contact.EMailAddress = warehouse_partner.email or ''
        # TODO fedex documentation asks for TIN number, but it seems to work without

        Address = self.factory.Address()
        Address.StreetLines = [remove_accents(warehouse_partner.street) or '',remove_accents(warehouse_partner.street2) or '']
        Address.City = remove_accents(warehouse_partner.city) or ''
        if warehouse_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            Address.StateOrProvinceCode = warehouse_partner.state_id.code or ''
        else:
            Address.StateOrProvinceCode = ''
        Address.PostalCode = warehouse_partner.zip or ''
        Address.CountryCode = warehouse_partner.country_id.code or ''

        self.RequestedShipment.Shipper = self.factory.Party()
        self.RequestedShipment.Shipper.Contact = Contact
        self.RequestedShipment.Shipper.Address = Address

    def set_recipient(self, recipient_partner):
        Contact = self.factory.Contact()
        if recipient_partner.is_company:
            Contact.PersonName = ''
            Contact.CompanyName = remove_accents(recipient_partner.name)
        else:
            Contact.PersonName = remove_accents(recipient_partner.name)
            Contact.CompanyName = remove_accents(recipient_partner.commercial_company_name) or ''
        Contact.PhoneNumber = recipient_partner.phone or ''
        Contact.EMailAddress = recipient_partner.email or ''

        Address = self.factory.Address()
        Address.StreetLines = [remove_accents(recipient_partner.street) or '', remove_accents(recipient_partner.street2) or '']
        Address.City = remove_accents(recipient_partner.city) or ''
        if recipient_partner.country_id.code in STATECODE_REQUIRED_COUNTRIES:
            Address.StateOrProvinceCode = recipient_partner.state_id.code or ''
        else:
            Address.StateOrProvinceCode = ''
        Address.PostalCode = recipient_partner.zip or ''
        Address.CountryCode = recipient_partner.country_id.code or ''

        self.RequestedShipment.Recipient = self.factory.Party()
        self.RequestedShipment.Recipient.Contact = Contact
        self.RequestedShipment.Recipient.Address = Address

    def shipment_request(self, dropoff_type, service_type, packaging_type, overall_weight_unit, saturday_delivery):
        self.RequestedShipment = self.factory.RequestedShipment()
        self.RequestedShipment.SpecialServicesRequested = self.factory.ShipmentSpecialServicesRequested()
        self.RequestedShipment.ShipTimestamp = datetime.now()
        self.RequestedShipment.DropoffType = dropoff_type
        self.RequestedShipment.ServiceType = service_type
        self.RequestedShipment.PackagingType = packaging_type
        # Resuest estimation of duties and taxes for international shipping
        if service_type in ['INTERNATIONAL_ECONOMY', 'INTERNATIONAL_PRIORITY']:
            self.RequestedShipment.EdtRequestType = 'ALL'
        else:
            self.RequestedShipment.EdtRequestType = 'NONE'
        self.RequestedShipment.PackageCount = 0
        self.RequestedShipment.TotalWeight = self.factory.Weight()
        self.RequestedShipment.TotalWeight.Units = overall_weight_unit
        self.RequestedShipment.TotalWeight.Value = 0
        self.listCommodities = []
        if saturday_delivery:
            timestamp_day = self.RequestedShipment.ShipTimestamp.strftime("%A")
            if (service_type == 'FEDEX_2_DAY' and timestamp_day == 'Thursday') or (service_type in ['PRIORITY_OVERNIGHT', 'FIRST_OVERNIGHT', 'INTERNATIONAL_PRIORITY'] and timestamp_day == 'Friday'):
                self.RequestedShipment.SpecialServicesRequested.SpecialServiceTypes.append('SATURDAY_DELIVERY')

    def set_currency(self, currency):
        # set perferred currency as GBP instead of UKL
        currency = 'GBP' if currency == 'UKL' else currency
        self.RequestedShipment.PreferredCurrency = currency
        # ask Fedex to include our preferred currency in the response
        self.RequestedShipment.RateRequestTypes = 'PREFERRED'

    def set_master_package(self, weight, package_count, master_tracking_id=False):
        self.RequestedShipment.TotalWeight.Value = weight
        self.RequestedShipment.PackageCount = package_count
        if master_tracking_id:
            self.RequestedShipment.MasterTrackingId = self.factory.TrackingId()
            self.RequestedShipment.MasterTrackingId.TrackingIdType = 'FEDEX'
            self.RequestedShipment.MasterTrackingId.TrackingNumber = master_tracking_id

    # weight_value, package_code=False, package_height=0, package_width=0, package_length=0,
    def add_package(self, carrier, delivery_package, fdx_company_currency, sequence_number=False, mode='shipping', po_number=False, dept_number=False, reference=False):
        package = self.factory.RequestedPackageLineItem()
        package_weight = self.factory.Weight()
        package_weight.Value = carrier._fedex_convert_weight(delivery_package.weight, carrier.fedex_weight_unit)
        package_weight.Units = self.RequestedShipment.TotalWeight.Units

        package.PhysicalPackaging = 'BOX'
        if delivery_package.packaging_type == 'YOUR_PACKAGING':
            package.Dimensions = self.factory.Dimensions()
            package.Dimensions.Height = int(delivery_package.dimension['height'])
            package.Dimensions.Width = int(delivery_package.dimension['width'])
            package.Dimensions.Length = int(delivery_package.dimension['length'])
            # TODO in master, add unit in product packaging and perform unit conversion
            package.Dimensions.Units = "IN" if self.RequestedShipment.TotalWeight.Units == 'LB' else 'CM'
        if po_number:
            po_reference = self.factory.CustomerReference()
            po_reference.CustomerReferenceType = 'P_O_NUMBER'
            po_reference.Value = po_number
            package.CustomerReferences.append(po_reference)
        if dept_number:
            dept_reference = self.factory.CustomerReference()
            dept_reference.CustomerReferenceType = 'DEPARTMENT_NUMBER'
            dept_reference.Value = dept_number
            package.CustomerReferences.append(dept_reference)
        if reference:
            customer_reference = self.factory.CustomerReference()
            customer_reference.CustomerReferenceType = 'CUSTOMER_REFERENCE'
            customer_reference.Value = reference
            package.CustomerReferences.append(customer_reference)

        if carrier.shipping_insurance:
            package.InsuredValue = self.factory.Money()
            insured_value = delivery_package.total_cost * carrier.shipping_insurance / 100
            pkg_order = delivery_package.order_id or delivery_package.picking_id.sale_id
            # Get the currency from the sale order if it exists, so that it matches that of customs_value
            if pkg_order:
                package.InsuredValue.Currency = _convert_curr_iso_fdx(pkg_order.currency_id.name)
                package.InsuredValue.Amount = float_repr(delivery_package.company_id.currency_id._convert(insured_value, pkg_order.currency_id, pkg_order.company_id, date.today()), 2)
            else:
                package.InsuredValue.Currency = fdx_company_currency
                package.InsuredValue.Amount = float_repr(insured_value, 2)

        package.Weight = package_weight
        if mode == 'rating':
            package.GroupPackageCount = 1
        if sequence_number:
            package.SequenceNumber = sequence_number

        if mode == 'rating':
            self.RequestedShipment.RequestedPackageLineItems.append(package)
        else:
            self.RequestedShipment.RequestedPackageLineItems = package

    # Rating stuff

    def start_rating_transaction(self, wsdl_path):
        settings = Settings(strict=False)
        self.client = Client(file_path(wsdl_path), plugins=[LogPlugin(self.debug_logger)], settings=settings)
        self.factory = self.client.type_factory('ns0')
        self.VersionId = self.factory.VersionId()
        self.VersionId.ServiceId = 'crs'
        self.VersionId.Major = '31'
        self.VersionId.Intermediate = '0'
        self.VersionId.Minor = '0'

    def rate(self, request):
        formatted_response = {'price': {}}
        try:
            self.response = self.client.service.getRates(WebAuthenticationDetail=request['WebAuthenticationDetail'],
                                                         ClientDetail=request['ClientDetail'],
                                                         TransactionDetail=request['TransactionDetail'],
                                                         Version=request['VersionId'],
                                                         RequestedShipment=request['RequestedShipment'])

            if (self.response.HighestSeverity != 'ERROR' and self.response.HighestSeverity != 'FAILURE'):
                if not getattr(self.response, "RateReplyDetails", False):
                    raise Exception("No rating found")
                for rating in self.response.RateReplyDetails[0].RatedShipmentDetails:
                    formatted_response['price'][rating.ShipmentRateDetail.TotalNetFedExCharge.Currency] = float(rating.ShipmentRateDetail.TotalNetFedExCharge.Amount)
                    if len(self.response.RateReplyDetails[0].RatedShipmentDetails) == 1:
                        if 'CurrencyExchangeRate' in self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail and self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail['CurrencyExchangeRate']:
                            formatted_response['price'][self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail.CurrencyExchangeRate.FromCurrency] = float(self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail.TotalNetFedExCharge.Amount) / float(self.response.RateReplyDetails[0].RatedShipmentDetails[0].ShipmentRateDetail.CurrencyExchangeRate.Rate)
            else:
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if (n.Severity == 'ERROR' or n.Severity == 'FAILURE')])
                formatted_response['errors_message'] = errors_message

            if any([n.Severity == 'WARNING' for n in self.response.Notifications]):
                warnings_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if n.Severity == 'WARNING'])
                formatted_response['warnings_message'] = warnings_message

        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Fedex Server Not Found"
        except Exception as e:
            formatted_response['errors_message'] = e.args[0]

        return formatted_response

    # Shipping stuff

    def start_shipping_transaction(self, wsdl_path):
        self.client = Client(file_path(wsdl_path), plugins=[LogPlugin(self.debug_logger)])
        self.factory = self.client.type_factory("ns0")
        self.VersionId = self.factory.VersionId()
        self.VersionId.ServiceId = 'ship'
        self.VersionId.Major = '28'
        self.VersionId.Intermediate = '0'
        self.VersionId.Minor = '0'

    def shipment_label(self, label_format_type, image_type, label_stock_type, label_printing_orientation, label_order):
        LabelSpecification = self.factory.LabelSpecification()
        LabelSpecification.LabelFormatType = label_format_type
        LabelSpecification.ImageType = image_type
        LabelSpecification.LabelStockType = label_stock_type
        LabelSpecification.LabelPrintingOrientation = label_printing_orientation
        LabelSpecification.LabelOrder = label_order
        self.RequestedShipment.LabelSpecification = LabelSpecification

    def commercial_invoice(self, document_stock_type, send_etd=False):
        shipping_document = self.factory.ShippingDocumentSpecification()
        shipping_document.ShippingDocumentTypes = "COMMERCIAL_INVOICE"
        commercial_invoice_detail = self.factory.CommercialInvoiceDetail()
        commercial_invoice_detail.Format = self.factory.ShippingDocumentFormat()
        commercial_invoice_detail.Format.ImageType = "PDF"
        commercial_invoice_detail.Format.StockType = document_stock_type
        shipping_document.CommercialInvoiceDetail = commercial_invoice_detail
        self.RequestedShipment.ShippingDocumentSpecification = shipping_document
        if send_etd:
            self.RequestedShipment.SpecialServicesRequested.SpecialServiceTypes.append('ELECTRONIC_TRADE_DOCUMENTS')
            etd_details = self.factory.EtdDetail()
            etd_details.RequestedDocumentCopies.append('COMMERCIAL_INVOICE')
            self.RequestedShipment.SpecialServicesRequested.EtdDetail = etd_details

    def shipping_charges_payment(self, shipping_charges_payment_account):
        self.RequestedShipment.ShippingChargesPayment = self.factory.Payment()
        self.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER'
        Payor = self.factory.Payor()
        Payor.ResponsibleParty = self.factory.Party()
        Payor.ResponsibleParty.AccountNumber = shipping_charges_payment_account
        self.RequestedShipment.ShippingChargesPayment.Payor = Payor

    def duties_payment(self, sender_party, responsible_account_number, payment_type):
        self.RequestedShipment.CustomsClearanceDetail.DutiesPayment = self.factory.Payment()
        self.RequestedShipment.CustomsClearanceDetail.DutiesPayment.PaymentType = payment_type
        if payment_type == 'SENDER':
            Payor = self.factory.Payor()
            Payor.ResponsibleParty = self.factory.Party()
            Payor.ResponsibleParty.Address = self.factory.Address()
            Payor.ResponsibleParty.Address.CountryCode = sender_party.country_id.code
            Payor.ResponsibleParty.AccountNumber = responsible_account_number
            self.RequestedShipment.CustomsClearanceDetail.DutiesPayment.Payor = Payor

    def customs_value(self, customs_value_currency, customs_value_amount, document_content):
        self.RequestedShipment.CustomsClearanceDetail = self.factory.CustomsClearanceDetail()
        if self.hasCommodities:
            self.RequestedShipment.CustomsClearanceDetail.Commodities = self.listCommodities
        self.RequestedShipment.CustomsClearanceDetail.CustomsValue = self.factory.Money()
        self.RequestedShipment.CustomsClearanceDetail.CustomsValue.Currency = customs_value_currency
        self.RequestedShipment.CustomsClearanceDetail.CustomsValue.Amount = float_repr(customs_value_amount, 2)
        if self.RequestedShipment.Shipper.Address.CountryCode == "IN" and self.RequestedShipment.Recipient.Address.CountryCode == "IN":
            if not self.RequestedShipment.CustomsClearanceDetail.CommercialInvoice:
                self.RequestedShipment.CustomsClearanceDetail.CommercialInvoice = self.factory.CommercialInvoice()
            else:
                del self.RequestedShipment.CustomsClearanceDetail.CommercialInvoice.TaxesOrMiscellaneousChargeType
            self.RequestedShipment.CustomsClearanceDetail.CommercialInvoice.Purpose = 'SOLD'
        # Old keys not requested anymore but still in WSDL; not removing them causes crash
        del self.RequestedShipment.CustomsClearanceDetail['ClearanceBrokerage']
        del self.RequestedShipment.CustomsClearanceDetail['FreightOnValue']

        self.RequestedShipment.CustomsClearanceDetail.DocumentContent = document_content

    def commodities(self, carrier, delivery_commodity, commodity_currency):
        self.hasCommodities = True
        commodity = self.factory.Commodity()
        commodity.UnitPrice = self.factory.Money()
        commodity.UnitPrice.Currency = commodity_currency
        commodity.UnitPrice.Amount = delivery_commodity.monetary_value
        commodity.NumberOfPieces = '1'
        commodity.CountryOfManufacture = delivery_commodity.country_of_origin

        commodity_weight = self.factory.Weight()
        commodity_weight.Value = carrier._fedex_convert_weight(delivery_commodity.product_id.weight * delivery_commodity.qty, carrier.fedex_weight_unit)
        commodity_weight.Units = carrier.fedex_weight_unit

        commodity.Weight = commodity_weight
        commodity.Description = re.sub(r'[\[\]<>;={}"|]', '', delivery_commodity.product_id.name)
        commodity.Quantity = delivery_commodity.qty
        commodity.QuantityUnits = 'EA'
        customs_value = self.factory.Money()
        customs_value.Currency = commodity_currency
        customs_value.Amount = delivery_commodity.monetary_value * delivery_commodity.qty
        commodity.CustomsValue = customs_value

        commodity.HarmonizedCode = delivery_commodity.product_id.hs_code.replace(".", "") if delivery_commodity.product_id.hs_code else ''

        self.listCommodities.append(commodity)

    def return_label(self, tracking_number, origin_date):
        return_details = self.factory.ReturnShipmentDetail()
        return_details.ReturnType = "PRINT_RETURN_LABEL"
        if tracking_number and origin_date:
            return_association = self.factory.ReturnAssociationDetail()
            return_association.TrackingNumber = tracking_number
            return_association.ShipDate = origin_date
            return_details.ReturnAssociation = return_association
        self.RequestedShipment.SpecialServicesRequested.SpecialServiceTypes.append("RETURN_SHIPMENT")
        self.RequestedShipment.SpecialServicesRequested.ReturnShipmentDetail = return_details
        if self.hasCommodities:
            bla = self.factory.CustomsOptionDetail()
            bla.Type = "FAULTY_ITEM"
            self.RequestedShipment.CustomsClearanceDetail.CustomsOptions = bla

    def process_shipment(self, request):
        formatted_response = {'tracking_number': 0.0,
                              'price': {},
                              'master_tracking_id': None,
                              'date': None}
        try:
            self.response = self.client.service.processShipment(WebAuthenticationDetail=request['WebAuthenticationDetail'],
                                                                ClientDetail=request['ClientDetail'],
                                                                TransactionDetail=request['TransactionDetail'],
                                                                Version=request['VersionId'],
                                                                RequestedShipment=request['RequestedShipment'])

            if (self.response.HighestSeverity != 'ERROR' and self.response.HighestSeverity != 'FAILURE'):
                formatted_response['tracking_number'] = self.response.CompletedShipmentDetail.CompletedPackageDetails[0].TrackingIds[0].TrackingNumber
                if 'CommitDate' in self.response.CompletedShipmentDetail.OperationalDetail:
                    formatted_response['date'] = self.response.CompletedShipmentDetail.OperationalDetail.CommitDate
                else:
                    formatted_response['date'] = date.today()

                if 'ShipmentRating' in self.response.CompletedShipmentDetail and self.response.CompletedShipmentDetail.ShipmentRating:
                    for rating in self.response.CompletedShipmentDetail.ShipmentRating.ShipmentRateDetails:
                        formatted_response['price'][rating.TotalNetFedExCharge.Currency] = float(rating.TotalNetFedExCharge.Amount)
                        if 'CurrencyExchangeRate' in rating and rating.CurrencyExchangeRate:
                            formatted_response['price'][rating.CurrencyExchangeRate.FromCurrency] = float(rating.TotalNetFedExCharge.Amount / rating.CurrencyExchangeRate.Rate)
                else:
                    formatted_response['price']['USD'] = 0.0
                if 'MasterTrackingId' in self.response.CompletedShipmentDetail:
                    formatted_response['master_tracking_id'] = self.response.CompletedShipmentDetail.MasterTrackingId.TrackingNumber

            else:
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if (n.Severity == 'ERROR' or n.Severity == 'FAILURE')])
                formatted_response['errors_message'] = errors_message

            if any([n.Severity == 'WARNING' for n in self.response.Notifications]):
                warnings_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if n.Severity == 'WARNING'])
                formatted_response['warnings_message'] = warnings_message

        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Fedex Server Not Found"

        return formatted_response

    def _get_labels(self, file_type):
        labels = [self.get_label()]
        if file_type.upper() in ['PNG'] and self.response.CompletedShipmentDetail.CompletedPackageDetails[0].PackageDocuments:
            for auxiliary in self.response.CompletedShipmentDetail.CompletedPackageDetails[0].PackageDocuments[0].Parts:
                labels.append(auxiliary.Image)

        return labels

    def get_label(self):
        return self.response.CompletedShipmentDetail.CompletedPackageDetails[0].Label.Parts[0].Image

    def get_document(self):
        if self.response.CompletedShipmentDetail.ShipmentDocuments:
            return self.response.CompletedShipmentDetail.ShipmentDocuments[0].Parts[0].Image
        else:
            return False

    # Deletion stuff

    def set_deletion_details(self, tracking_number):
        self.TrackingId = self.factory.TrackingId()
        self.TrackingId.TrackingIdType = 'FEDEX'
        self.TrackingId.TrackingNumber = tracking_number

        self.DeletionControl = self.factory.DeletionControlType('DELETE_ALL_PACKAGES')

    def delete_shipment(self, request):
        formatted_response = {'delete_success': False}
        try:
            # Here, we send the Order 66
            self.response = self.client.service.deleteShipment(WebAuthenticationDetail=request['WebAuthenticationDetail'],
                                                               ClientDetail=request['ClientDetail'],
                                                               TransactionDetail=request['TransactionDetail'],
                                                               Version=request['VersionId'],
                                                               TrackingId=request['TrackingId'],
                                                               DeletionControl=request['DeletionControl'])

            if (self.response.HighestSeverity != 'ERROR' and self.response.HighestSeverity != 'FAILURE'):
                formatted_response['delete_success'] = True
            else:
                errors_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if (n.Severity == 'ERROR' or n.Severity == 'FAILURE')])
                formatted_response['errors_message'] = errors_message

            if any([n.Severity == 'WARNING' for n in self.response.Notifications]):
                warnings_message = '\n'.join([("%s: %s" % (n.Code, n.Message)) for n in self.response.Notifications if n.Severity == 'WARNING'])
                formatted_response['warnings_message'] = warnings_message

        except Fault as fault:
            formatted_response['errors_message'] = fault
        except IOError:
            formatted_response['errors_message'] = "Fedex Server Not Found"

        return formatted_response

def _convert_curr_fdx_iso(code):
    curr_match = {v: k for k, v in FEDEX_CURR_MATCH.items()}
    return curr_match.get(code, code)


def _convert_curr_iso_fdx(code):
    return FEDEX_CURR_MATCH.get(code, code)
