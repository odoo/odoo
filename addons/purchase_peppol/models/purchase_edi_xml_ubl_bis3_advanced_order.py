import datetime

from lxml import etree

from odoo import models
from odoo.tools import html2plaintext
from odoo.tools.float_utils import float_compare

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

    def build_order_xml(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        document_node = super()._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        xml_content = dict_to_xml(document_node, template=Order, nsmap=nsmap)

        return etree.tostring(xml_content, xml_declaration=True, pretty_print=True, encoding='utf-8')

    # -------------------------------------------------------------------------
    # Order export
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

    def _add_purchase_order_line_id_nodes(self, line_node, vals):
        """
        OVERRIDE of `purchase.edi.xml.ubl_bis3`: instead of simple line index, use record id to keep
        track of order line changes.
        """
        line_node['cbc:ID'] = {'_text': vals['base_line']['record'].id}

    # -------------------------------------------------------------------------
    # Order import
    # -------------------------------------------------------------------------

    def _retrieve_line_vals(self, tree, document_type=False, qty_factor=1):
        """
        EXTENDS `account.edi.common`: add line_ref on purchase order lines. This reference allows us
        to amend orders or generate order change document.

        :return dict: line values
        """
        xpath_dict = self._get_line_xpaths(document_type, qty_factor)

        line_item_id = None
        line_item_id_node = tree.find(xpath_dict['line_item_id'])
        if line_item_id_node is not None:
            line_item_id = line_item_id_node.text

        return {
            **super()._retrieve_line_vals(tree, document_type, qty_factor),
            'line_item_id': line_item_id,
        }

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        """
        EXTENDS `account.edi.xml.ubl_bis3` to update dictionary key used for extracting document
        line item ID. This is crucial for advanced order to match line items to update on order
        change request.

        :return dict: line XPath string dict
        """
        return {
            **super()._get_line_xpaths(document_type=document_type, qty_factor=qty_factor),
            'line_item_id': './{*}ID',
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
        order_change_seq = vals['order_change_seq']
        document_node.update({
            'cbc:CustomizationID': {'_text': 'urn:fdc:peppol.eu:poacc:trns:order_change:3'},
            'cbc:ID': {'_text': f"{purchase_order['name']}-{order_change_seq}"},
            'cbc:SequenceNumberID': {'_text': order_change_seq},
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

        order = vals['purchase_order']
        last_applied_order = next(t for t in order.edi_tracker_ids if t.state == 'accepted')
        tree = self.env['account.move']._to_files_data(last_applied_order.attachment_id)[0]['xml_tree']
        document_type = last_applied_order.document_type

        if document_type == 'order':
            edi_parser = self.env['purchase.edi.xml.ubl_bis3_order']
        elif document_type == 'order_change':
            edi_parser = self.env['purchase.edi.xml.ubl_bis3_order_change']

        lines_vals = []
        for line_tree in tree.iterfind('./{*}OrderLine/{*}LineItem'):
            line_vals = edi_parser._retrieve_line_vals(line_tree, document_type)
            if document_type == 'order_change' and line_vals['line_status_code'] == '2':
                continue  # The imported line is deleted line; ignore the line
            lines_vals.append(line_vals)

        # TODO: In `purchase.edi.xml.ubl_bis3` I wish we could use a hook that generates a order
        # line dict instead of using multiple fixed hooks. That way, adding elements to order line
        # XML would be easier and more readable.
        for base_line in vals['base_lines']:
            # Find line node to update
            line_node = next((
                item for item in document_node['cac:OrderLine']
                if item['cac:LineItem']['cbc:ID']['_text'] == base_line['id']
            ), None)

            # Find original line value, if any
            origin_line_idx = next((
                i for i, line_vals in enumerate(lines_vals)
                if line_vals['line_item_id'] == str(base_line['id'])
            ), None)

            if origin_line_idx is not None:
                origin_line_vals = lines_vals.pop(origin_line_idx)

                if base_line['quantity'] != origin_line_vals['quantity'] \
                or base_line['product_id']['display_name'] != origin_line_vals['name'] \
                or float_compare(base_line['discount'], origin_line_vals['discount'], 2) \
                or float_compare(base_line['price_unit'], origin_line_vals['price_unit'], 2):
                    line_node['cac:LineItem']['cbc:LineStatusCode'] = {'_text': '3'}  # Changed
                else:
                    line_node['cac:LineItem']['cbc:LineStatusCode'] = {'_text': '4'}  # No action

            else:
                line_node['cac:LineItem']['cbc:LineStatusCode'] = {'_text': '1'}  # Added

        # The remaining `lines_vals` are deleted lines
        for line_vals in lines_vals:
            # Only add the bare minimum
            document_node['cac:OrderLine'].append({
                'cac:LineItem': {
                    'cbc:ID': {'_text': line_vals['line_item_id']},
                    'cbc:LineStatusCode': {'_text': '2'},
                    'cbc:Quantity': {'_text': line_vals['quantity']},
                    'cbc:LineExtensionAmount': {'_text': 0},  # Importing XML expects line subtotal as mandatory field. See _retrieve_line_vals()
                    'cac:Price': {  # Importing XML throws error if no price information is provided.
                        'cbc:PriceAmount': {'_text': 0},
                    },
                    'cac:Item': {
                        'cbc:Name': {'_text': line_vals['name']},
                    },
                },
            })

    # -------------------------------------------------------------------------
    # Import from XML
    # -------------------------------------------------------------------------

    def _retrieve_line_vals(self, tree, document_type=False, qty_factor=1):
        """
        EXTENDS `purchase.edi.xml.ubl_bis3_order` to add 'line_status_code' value to the line
        values. This method is used to filter out deleted lines (code: 2) when importing the order
        lines for comparison.
        """
        line_status_code_node = tree.find('./{*}LineStatusCode')
        if line_status_code_node is not None:
            line_status_code = line_status_code_node.text

        return {
            'line_status_code': line_status_code,
            **super()._retrieve_line_vals(tree, document_type, qty_factor),
        }

    def build_order_change_xml(self, purchase_order):
        order_change_seq = len([t for t in purchase_order.edi_tracker_ids if t.document_type == 'order_change']) + 1

        vals = {
            'purchase_order': purchase_order,
            'order_change_seq': order_change_seq,
        }
        document_node = self._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        nsmap.update({
            None: "urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2",
        })
        xml_content = dict_to_xml(document_node, template=OrderChange, nsmap=nsmap)

        return etree.tostring(xml_content, xml_declaration=True, pretty_print=True, encoding='utf-8')


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
        nsmap.update({
            None: "urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2",
        })
        xml_content = dict_to_xml(document_node, template=OrderCancel, nsmap=nsmap)

        return etree.tostring(xml_content, xml_declaration=True, pretty_print=True, encoding='utf-8')

class PurchaseEdiXmlUbl_Bis3_OrderResponseAdvanced(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order_response_advanced'
    _inherit = ['purchase.edi.xml.ubl_bis3_order']
    _description = "Import PEPPOL BIS 3 Order Response Advanced Transaction 3.1"
