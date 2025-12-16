import datetime

from lxml import etree

from odoo import models
from odoo.tools import html2plaintext

from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.tools import Order, OrderCancel, OrderChange


class PurchaseEdiXmlUbl_Bis3_Order(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order'
    _inherit = ['purchase.edi.xml.ubl_bis3']
    _description = "Export Purchase Order to PEPPOL BIS 3 Order Transaction 3.6"

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------

    def _add_purchase_order_header_nodes(self, document_node, vals):
        """ EXTENDS `purchase.edi.xml.ubl_bis3`
        """
        super()._add_purchase_order_header_nodes(document_node, vals)
        purchase_order = vals['purchase_order']
        document_node.update({
            'cbc:ProfileID': {'_text': 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'},
            # Add cbc:IssueTime? How do we deal with different timezones?
            # Add cbc:CustomerReference? ref: https://docs.peppol.eu/poacc/upgrade-3/2025-Q2/syntax/Order/cbc-CustomerReference/
            'cac:ValidityPeriod': {
                'cbc:EndDate': {'_text': purchase_order.date_order.date()},
            },
        })

    def _add_purchase_order_seller_supplier_party_nodes(self, document_node, vals):
        """
        EXTENDS `purchase.edi.xml.ubl_bis3`. The supplier party should not have 'cac:PartyTaxScheme'
        """
        super()._add_purchase_order_seller_supplier_party_nodes(document_node, vals)

        document_node['cac:SellerSupplierParty']['cac:Party']['cac:PartyTaxScheme'] = None

    def _add_purchase_order_delivery_nodes(self, document_node, vals):
        """
        EXTENDS `purchase.edi.xml.ubl_bis3`
        """
        super()._add_purchase_order_delivery_nodes(document_node, vals)

        delivery_party = document_node['cac:Delivery']['cac:DeliveryParty']
        delivery_party.pop('cbc:EndpointID', None)
        delivery_party.pop('cac:PartyTaxScheme', None)
        delivery_party.pop('cac:PartyLegalEntity', None)

    def _add_purchase_order_tax_total_nodes(self, document_node, vals):
        super()._add_purchase_order_tax_total_nodes(document_node, vals)

        document_node['cac:TaxTotal']['cac:TaxSubtotal'] = None

    # -------------------------------------------------------------------------
    # Export to XML
    # -------------------------------------------------------------------------

    def _send_xml(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        document_node = super()._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        xml_content = dict_to_xml(document_node, template=Order, nsmap=nsmap)

        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%H:%M:%S")

        filename = f"/home/odoo/Documents/BIS Advanced Order/order/Order_{timestamp_str}.xml"
        try:
            etree.ElementTree(xml_content).write(filename,
                              pretty_print=True,
                              xml_declaration=True,
                              encoding='utf-8')
        except OSError as e:
            print(f"Error writing to file: {e}")

    # -------------------------------------------------------------------------
    # Order export common
    # -------------------------------------------------------------------------
    def _get_document_nsmap(self, vals):
        return {
            None: {
                'order': "urn:oasis:names:specification:ubl:schema:xsd:Order-2",
                'order_change': "urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2",
                'order_cancel': "urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2",
                'order_response_advanced': "urn:oasis:names:specification:ubl:schema:xsd:OrderResponse-2",
            }[vals['document_type']],
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        }


class PurchaseEdiXmlUbl_Bis3_OrderChange(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order_change'
    _inherit = ['purchase.edi.xml.ubl_bis3_order']
    _description = "Export Purchase Order to PEPPOL BIS 3 Order Change Transaction 3.1"

    # -------------------------------------------------------------------------
    # Overrides
    # -------------------------------------------------------------------------

    def _add_purchase_order_header_nodes(self, document_node, vals):
        """ EXTENDS `purchase.edi.xml.ubl_bis3`
        """
        super()._add_purchase_order_header_nodes(document_node, vals)

        purchase_order = vals['purchase_order']
        document_node.update({
            'cbc:CustomizationID': {'_text': 'urn:fdc:peppol.eu:poacc:trns:order_change:3'},
            'cbc:ID': {'_text': f"{purchase_order['name']}-{purchase_order.order_change_sequence_no}"},
            'cbc:SequenceNumberID': {'_text': purchase_order.order_change_sequence_no},
            # 'cbc:IssueDate': {'_text': purchase_order.create_date.date()},
            # What do we do with the issue date?
            'cac:OrderReference': {
                'cbc:ID': {'_text': purchase_order['name']},
            },
        })
        del document_node['cbc:OrderTypeCode']

    def _add_purchase_order_line_nodes(self, document_node, vals):
        """ EXTENDS `purchase.edi.xml.ubl_bis3`
        """
        super()._add_purchase_order_line_nodes(document_node, vals)

        # TODO: In `purchase.edi.xml.ubl_bis3` I wish we could use a hook that generates a order
        # line dict instead of using multiple fixed hooks. That way, adding elements to order line
        # XML would be easier and more readable.
        for order_line in document_node['cac:OrderLine']:
            item = order_line['cac:LineItem']
            # Let's assume they accept the suggestion
            item['cbc:LineStatusCode'] = {
                '_text': '3',
            }

    def send_xml(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        # document_node = super()._get_purchase_order_node(vals)
        document_node = self._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        nsmap.update({
            None: "urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2",
        })
        xml_content = dict_to_xml(document_node, template=OrderChange, nsmap=nsmap)

        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%H:%M:%S")

        filename = f"/home/odoo/Documents/advanced-order/order/AO_{timestamp_str}.xml"
        try:
            etree.ElementTree(xml_content).write(filename,
                              pretty_print=True,
                              xml_declaration=True,
                              encoding='utf-8')
        except OSError as e:
            print(f"Error writing to file: {e}")


class PurchaseEdiXmlUbl_Bis3_OrderCancel(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order_cancel'
    _inherit = ['purchase.edi.xml.ubl_bis3_order']
    _description = "Export Purchase Order to PEPPOL BIS 3 Order Cancellation Transaction 3.0"

    def _add_purchase_order_config_vals(self, vals):
        super()._add_purchase_order_config_vals(vals)
        vals.update({'document_type': 'order_cancel'})

    def _get_purchase_order_node(self, vals):
        self._add_purchase_order_config_vals(vals)

        document_node = {}
        self._add_purchase_order_header_nodes(document_node, vals)
        self._add_purchase_order_buyer_customer_party_nodes(document_node, vals)
        self._add_purchase_order_seller_supplier_party_nodes(document_node, vals)
        return document_node

    def _add_purchase_order_header_nodes(self, document_node, vals):
        purchase_order = vals['purchase_order']
        document_node.update({
            'cbc:CustomizationID': {'_text': 'urn:fdc:peppol.eu:poacc:trns:order_cancellation:3'},
            'cbc:ProfileID': {'_text': 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'},
            'cbc:ID': {'_text': f"{purchase_order.name}-cancellation"},  # Add sequence? Might be able to send multiple
            'cbc:IssueDate': {'_text': purchase_order.create_date.date()},
            'cbc:Note': {'_text': html2plaintext(purchase_order.note)} if purchase_order.note else None,
            'cbc:CancellationNote': {'_text': "Cancellation Note. TODO"},
            'cac:OrderReference': {
                'cbc:ID': {'_text': purchase_order.name},
            },
        })

    def build_order_cancel_xml(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        document_node = self._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        xml_content = dict_to_xml(document_node, template=OrderCancel, nsmap=nsmap)

        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d_%H:%M:%S")

        filename = f"/home/odoo/test-generated/order-cancel/AO_{timestamp_str}.xml"
        try:
            etree.ElementTree(xml_content).write(filename,
                              pretty_print=True,
                              xml_declaration=True,
                              encoding='utf-8')
        except OSError as e:
            print(f"Error writing to file: {e}")


class PurchaseEdiXmlUbl_Bis3_OrderResponseAdvanced(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order_response_advanced'
    _inherit = ['purchase.edi.xml.ubl_bis3_order']
    _description = "Import PEPPOL BIS 3 Order Response Advanced Transaction 3.1"
