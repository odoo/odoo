import datetime

from lxml import etree

from odoo import models

from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.tools import Order


class PurchaseEdiXmlBis3AdvancedOrder(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_advanced_order'
    _inherit = ['purchase.edi.xml.ubl_bis3']
    _description = "Purchase Peppol Order Transaction 3.6"

    # -------------------------------------------------------------------------
    # Purchase Order EDI Export
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

    def _add_purchase_order_buyer_customer_party_nodes(self, document_node, vals):
        """ EXTENDS `purchase.edi.xml.ubl_bis3`
        """
        super()._add_purchase_order_buyer_customer_party_nodes(document_node, vals)

        if buyer := vals['purchase_order']['user_id']:
            document_node['cac:BuyerCustomerParty']['cac:Party']['cac:PartyName'] = {
                'cbc:Name': {'_text': buyer.name},
            }

    def _add_purchase_order_seller_supplier_party_nodes(self, document_node, vals):
        """ EXTENDS `purchase.edi.xml.ubl_bis3`
        """
        super()._add_purchase_order_seller_supplier_party_nodes(document_node, vals)

        document_node['cac:SellerSupplierParty']['cac:Party']['cac:PartyTaxScheme'] = None

    def _add_purchase_order_delivery_nodes(self, document_node, vals):
        """ EXTENDS `purchase.edi.xml.ubl_bis3`
        """
        super()._add_purchase_order_delivery_nodes(document_node, vals)

        delivery_party = document_node['cac:Delivery']['cac:DeliveryParty']
        delivery_party['cbc:EndpointID'] = None
        delivery_party['cac:PartyTaxScheme'] = None
        delivery_party['cac:PartyLegalEntity'] = None

    def _add_purchase_order_tax_total_nodes(self, document_node, vals):
        super()._add_purchase_order_tax_total_nodes(document_node, vals)

        document_node['cac:TaxTotal']['cac:TaxSubtotal'] = None

    # -------------------------------------------------------------------------
    # Send logic
    # -------------------------------------------------------------------------

    def send_xml(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        document_node = super()._get_purchase_order_node(vals)
        xml_content = dict_to_xml(document_node, template=Order, nsmap=self._get_document_nsmap(vals))

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
