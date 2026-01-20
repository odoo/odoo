from lxml import etree

from odoo import Command, models
from odoo.tools import html2plaintext
from odoo.tools.float_utils import float_compare

from odoo.addons.account.tools import dict_to_xml
from odoo.addons.l10n_sg_purchase_peppol.tools.peppol_advanced_order import (
    Order,
    OrderCancel,
    OrderChange,
)


class PurchaseEdiXmlUbl_Bis3_Order(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order'
    _inherit = ['purchase.edi.xml.ubl_bis3']
    _description = 'Export Purchase Order to PEPPOL BIS 3 Order Transaction 3.6'

    # -------------------------------------------------------------------------
    # Export to XML
    # -------------------------------------------------------------------------

    def _add_purchase_order_header_nodes(self, document_node, vals):
        """EXTENDS `purchase.edi.xml.ubl_bis3`"""
        super()._add_purchase_order_header_nodes(document_node, vals)

        partner = vals['purchase_order'].user_id
        document_node.update({'cbc:CustomerReference': {'_text': partner.ref}})
        if not document_node.get('cbc:Note'):
            document_node['cbc:Note'] = {'_text': 'Hardcoded document note for testing.'}

    def _add_purchase_order_buyer_customer_party_nodes(self, document_node, vals):
        """EXTENDS `purchase.edi.xml.ubl_bis3`. Hardcoded contact for testing."""
        super()._add_purchase_order_buyer_customer_party_nodes(document_node, vals)
        document_node['cac:BuyerCustomerParty']['cac:Party']['cac:Contact'] = {
            'cbc:Name': {'_text': 'test customer'},
            'cbc:ElectronicMail': {'_text': 'test@test.com'},
        }

    def _add_purchase_order_seller_supplier_party_nodes(self, document_node, vals):
        """
        EXTENDS `purchase.edi.xml.ubl_bis3`. The supplier party should not have 'cac:PartyTaxScheme'
        """
        super()._add_purchase_order_seller_supplier_party_nodes(document_node, vals)

        document_node['cac:SellerSupplierParty']['cac:Party']['cac:PartyTaxScheme'] = (
            None
        )

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
        """
        EXTENDS `purchase.edi.xml.ubl_bis3`: keep only the first tax total node.
        """
        super()._add_purchase_order_tax_total_nodes(document_node, vals)

        if len(document_node['cac:TaxTotal']) > 1:
            # Underlying logic creates two tax total nodes if the currency is different from the
            # company currency. We keep only the one matching the requested currency.
            tax_node_idx = None
            for idx, tax_total in enumerate(document_node['cac:TaxTotal']):
                if tax_total.get('_currency') == vals.get('currency_od'):
                    tax_node_idx = idx
                    break
            if tax_node_idx is not None:
                document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal'][tax_node_idx]]
            else:
                document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal'][0]]

    def _add_purchase_order_line_id_nodes(self, line_node, vals):
        """
        OVERRIDE of `purchase.edi.xml.ubl_bis3`: instead of simple line index, use record id to keep
        track of order line changes.
        """
        order_line = vals['base_line']['record']
        if not order_line.l10n_sg_ubl_line_item_ref:
            order_line.l10n_sg_ubl_line_item_ref = str(order_line.id)
        line_node['cbc:ID'] = {'_text': order_line.l10n_sg_ubl_line_item_ref}

    def _add_purchase_order_line_delivery_nodes(self, line_node):
        """
        EXTENDS `purchase.edi.xml.ubl_bis3`: hardcoded RequestedDeliveryPeriod for testing.
        There is no line-level delivery date field on purchase.order.line, so fixed values are
        used to exercise the sale-side import of cac:RequestedDeliveryPeriod.
        """
        line_node['cac:Delivery'] = {
            'cac:RequestedDeliveryPeriod': {
                'cbc:StartDate': {'_text': '2025-01-01'},
                'cbc:StartTime': {'_text': '09:00:00'},
                'cbc:EndDate': {'_text': '2025-12-31'},
                'cbc:EndTime': {'_text': '17:00:00'},
            },
        }

    def _add_purchase_order_line_nodes(self, document_node, vals):
        """EXTENDS `purchase.edi.xml.ubl_bis3`: inject hardcoded delivery period and line note into each line."""
        super()._add_purchase_order_line_nodes(document_node, vals)
        for order_line_node in document_node.get('cac:OrderLine', []):
            self._add_purchase_order_line_delivery_nodes(order_line_node['cac:LineItem'])
            order_line_node['cbc:Note'] = {'_text': 'Hardcoded line note for testing.'}

    def _ubl_get_tax_total_node(self, vals, tax_total):
        """
        EXTENDS `purchase.edi.xml.ubl_bis3`: generate the tax total node without 'cac:TaxSubtotal'.
        """
        tax_total_node = super()._ubl_get_tax_total_node(vals, tax_total)
        tax_total_node.pop('cac:TaxSubtotal', None)
        # purchase.edi.ubl_bis3._add_purchase_order_monetary_total_nodes() expects a list of tax total nodes
        return tax_total_node

    def build_order_xml(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        document_node = super()._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        xml_content = dict_to_xml(document_node, template=Order, nsmap=nsmap)

        return etree.tostring(
            xml_content, xml_declaration=True, pretty_print=True, encoding='utf-8'
        )

    # -------------------------------------------------------------------------
    # Import from XML
    # -------------------------------------------------------------------------

    def _retrieve_line_vals(self, record, tree, document_type=False, qty_factor=1):
        """
        EXTENDS `account.edi.common`: add line_ref on purchase order lines. This reference allows us
        to amend orders or generate line reference for creating order change document.

        :return dict: line values
        """
        xpath_dict = self._get_line_xpaths(document_type, qty_factor)

        line_item_id = None
        line_item_id_node = tree.find(xpath_dict['line_item_id'])
        if line_item_id_node is not None:
            line_item_id = line_item_id_node.text

        return {
            'l10n_sg_ubl_line_item_ref': line_item_id,
            **super()._retrieve_line_vals(record, tree, document_type, qty_factor),
        }

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        """
        EXTENDS `account.edi.xml.ubl_bis3` to update dictionary key used for extracting document
        line item ID. This is crucial for advanced order to match line items to identify lines to
        update.

        :return dict: line XPath string dict
        """
        return {
            **super()._get_line_xpaths(
                document_type=document_type, qty_factor=qty_factor
            ),
            'line_item_id': './{*}ID',
            'delivered_qty': './{*}Quantity',
        }


class PurchaseEdiXmlUbl_Bis3_OrderChange(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order_change'
    _inherit = ['purchase.edi.xml.ubl_bis3_order']
    _description = 'Export Purchase Order to PEPPOL BIS 3 Order Change Transaction 3.1'

    # -------------------------------------------------------------------------
    # Export to XML
    # -------------------------------------------------------------------------

    def _add_purchase_order_header_nodes(self, document_node, vals):
        """EXTENDS `purchase.edi.xml.ubl_bis3`"""
        super()._add_purchase_order_header_nodes(document_node, vals)

        purchase_order = vals['purchase_order']
        order_change_seq = vals['order_change_seq']
        document_node.update(
            {
                'cbc:CustomizationID': {
                    '_text': 'urn:fdc:peppol.eu:poacc:trns:order_change:3'
                },
                'cbc:ProfileID': {
                    '_text': 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'
                },
                'cbc:ID': {
                    '_text': f'{purchase_order.name}-order_change-{order_change_seq}'
                },
                'cbc:SequenceNumberID': {'_text': order_change_seq},
                'cac:OrderReference': {
                    'cbc:ID': {'_text': purchase_order['name']},
                },
            }
        )
        del document_node['cbc:OrderTypeCode']

    def _add_purchase_order_line_nodes(self, document_node, vals):
        """
        EXTENDS `purchase.edi.xml.ubl_bis3`. Order change line export compares current PO lines to
            the last accepted order document to determine the line status code.
        """
        super()._add_purchase_order_line_nodes(document_node, vals)

        order = vals['purchase_order']
        last_applied_order = next(
            t for t in order.l10n_sg_peppol_order_tx_ids if t.state == 'accepted'
        )
        tree = self.env['account.move']._to_files_data(
            last_applied_order.attachment_id
        )[0]['xml_tree']
        document_type = last_applied_order.document_type

        if document_type == 'order':
            edi_parser = self.env['purchase.edi.xml.ubl_bis3_order']
        elif document_type == 'order_change':
            edi_parser = self.env['purchase.edi.xml.ubl_bis3_order_change']

        order = vals['purchase_order']
        lines_vals = []
        for line_tree in tree.iterfind('./{*}OrderLine/{*}LineItem'):
            line_vals = edi_parser._retrieve_line_vals(order, line_tree, document_type)
            if document_type == 'order_change' and line_vals['line_status_code'] == '2':
                continue  # The imported line is deleted line; ignore the line
            lines_vals.append(line_vals)

        for base_line in vals['base_lines']:
            # Find line node to update
            line_node = next(
                (
                    item
                    for item in document_node['cac:OrderLine']
                    if item['cac:LineItem']['cbc:ID']['_text']
                    == base_line['record'].l10n_sg_ubl_line_item_ref
                ),
                None,
            )

            # Find original line value, if any
            origin_line_idx = next(
                (
                    i
                    for i, line_vals in enumerate(lines_vals)
                    if line_vals['l10n_sg_ubl_line_item_ref']
                    == base_line['record'].l10n_sg_ubl_line_item_ref
                ),
                None,
            )

            if origin_line_idx is not None:
                origin_line_vals = lines_vals.pop(origin_line_idx)

                if (
                    base_line['quantity'] != origin_line_vals['product_qty']
                    or base_line['product_id']['display_name']
                    != origin_line_vals['name']
                    or float_compare(
                        base_line['discount'], origin_line_vals['discount'], 2
                    )
                    or float_compare(
                        base_line['price_unit'], origin_line_vals['price_unit'], 2
                    )
                ):
                    line_node['cac:LineItem']['cbc:LineStatusCode'] = {
                        '_text': '3'
                    }  # Changed
                else:
                    line_node['cac:LineItem']['cbc:LineStatusCode'] = {
                        '_text': '4'
                    }  # No action

            else:
                line_node['cac:LineItem']['cbc:LineStatusCode'] = {
                    '_text': '1'
                }  # Added

        # The remaining `lines_vals` are deleted lines
        for line_vals in lines_vals:
            product_uom_id = line_vals.get('product_uom_id')
            product_uom = (
                self.env['uom.uom'].browse(product_uom_id)
                if product_uom_id
                else self.env.ref('uom.product_uom_unit')
            )
            document_node['cac:OrderLine'].append(
                {
                    'cac:LineItem': {
                        'cbc:ID': {'_text': line_vals['l10n_sg_ubl_line_item_ref']},
                        'cbc:LineStatusCode': {'_text': '2'},
                        'cbc:Quantity': {
                            '_text': line_vals['product_qty'],
                            'unitCode': self._get_uom_unece_code(product_uom),
                        },
                        'cbc:LineExtensionAmount': {  # Importing XML expects line subtotal as mandatory field. See sale EDI _retrieve_line_vals()
                            '_text': 0,
                            'currencyID': order.currency_id.name,
                        },
                        'cac:Price': {  # Importing XML throws error if no price information is provided.
                            'cbc:PriceAmount': {
                                '_text': 0,
                                'currencyID': order.currency_id.name,
                            },
                        },
                        'cac:Item': {
                            'cbc:Name': {'_text': line_vals['name']},
                        },
                    },
                }
            )

    def revert_order_change(self, order, order_tx):
        """
        Revert the order to the order transaction's attachment. This method is used to revert the order
        to the last accepted EDI order or order change document in case of order change rejection.

        :param order: Purchase order to revert
        :param order_tx: Order transaction to revert the order to
        """
        tree = self.env['account.move']._to_files_data(order_tx.attachment_id)[0][
            'xml_tree'
        ]
        document_type = order_tx.document_type

        if document_type == 'order':
            edi_parser = self.env['purchase.edi.xml.ubl_bis3_order']
        elif document_type == 'order_change':
            edi_parser = self.env['purchase.edi.xml.ubl_bis3_order_change']
        else:
            raise ValueError(f'Invalid document type: {document_type}')

        order_vals, _ = edi_parser._retrieve_order_vals(order, tree)
        order_lines_vals = [line_cmd[2] for line_cmd in order_vals['order_line']]

        for order_line in order.order_line:
            origin_line_idx = next(
                (
                    i
                    for i, order_line_vals in enumerate(order_lines_vals)
                    if order_line_vals['l10n_sg_ubl_line_item_ref']
                    == order_line.l10n_sg_ubl_line_item_ref
                ),
                None,
            )

            if origin_line_idx is None:
                # This line needs to be deleted, but the purchase order lines cannot be deleted.
                # We set the quantity to 0 instead as a workaround.
                order_line.product_qty = 0
            else:
                origin_line_vals = order_lines_vals.pop(origin_line_idx)
                order_line.write(origin_line_vals)

        # The remaining `order_lines_vals` are added lines
        for order_line_vals in order_lines_vals:
            order.write(
                {
                    'order_line': [Command.create(order_line_vals)],
                }
            )

    def build_order_change(self, purchase_order):
        order_change_seq = (
            len(
                [
                    t
                    for t in purchase_order.l10n_sg_peppol_order_tx_ids
                    if t.document_type == 'order_change'
                ]
            ) + 1
        )

        vals = {
            'purchase_order': purchase_order,
            'order_change_seq': order_change_seq,
        }
        document_node = self._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        nsmap.update(
            {
                None: 'urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2',
            }
        )
        xml_content = dict_to_xml(document_node, template=OrderChange, nsmap=nsmap)

        return {
            'xml_content': etree.tostring(
                xml_content, xml_declaration=True, pretty_print=True, encoding='utf-8'
            ),
            'sequence_number_id': document_node['cbc:SequenceNumberID']['_text'],
            'order_change_id': document_node['cbc:ID']['_text'],
        }

    # -------------------------------------------------------------------------
    # Import from XML
    # -------------------------------------------------------------------------

    def _retrieve_line_vals(self, record, tree, document_type=False, qty_factor=1):
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
            **super()._retrieve_line_vals(record, tree, document_type, qty_factor),
        }


class PurchaseEdiXmlUbl_Bis3_OrderCancel(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3_order_cancel'
    _inherit = ['purchase.edi.xml.ubl_bis3_order']
    _description = (
        'Export Purchase Order to PEPPOL BIS 3 Order Cancellation Transaction 3.0'
    )

    # -------------------------------------------------------------------------
    # Export to XML
    # -------------------------------------------------------------------------

    def _get_purchase_order_node(self, vals):
        self._add_purchase_order_config_vals(vals)
        vals['base_lines'] = []  # Cancel has no line items; required by _ubl_add_party_tax_scheme_nodes

        document_node = {}
        self._add_purchase_order_header_nodes(document_node, vals)
        self._add_purchase_order_buyer_customer_party_nodes(document_node, vals)
        self._add_purchase_order_seller_supplier_party_nodes(document_node, vals)
        return document_node

    def _add_purchase_order_header_nodes(self, document_node, vals):
        purchase_order = vals['purchase_order']
        order_cancel_seq = len(
            [
                t
                for t in purchase_order.l10n_sg_peppol_order_tx_ids
                if t.document_type == 'order_cancel'
            ]
        )

        document_node.update(
            {
                'cbc:CustomizationID': {
                    '_text': 'urn:fdc:peppol.eu:poacc:trns:order_cancellation:3'
                },
                'cbc:ProfileID': {
                    '_text': 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'
                },
                'cbc:ID': {
                    '_text': f'{purchase_order.name}-order_cancel-{order_cancel_seq}'
                },
                'cbc:IssueDate': {'_text': purchase_order.create_date.date()},
                'cbc:Note': {'_text': html2plaintext(purchase_order.note)}
                if purchase_order.note
                else None,
                'cbc:CancellationNote': {
                    '_text': 'User requested cancellation of the order.'
                },  # TODO: Allow user to add a cancellation note
                'cac:OrderReference': {
                    'cbc:ID': {'_text': purchase_order.name},
                },
            }
        )

    def build_order_cancel_xml(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        document_node = self._get_purchase_order_node(vals)
        nsmap = self._get_document_nsmap(vals)
        nsmap.update(
            {
                None: 'urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2',
            }
        )
        xml_content = dict_to_xml(document_node, template=OrderCancel, nsmap=nsmap)

        return etree.tostring(
            xml_content, xml_declaration=True, pretty_print=True, encoding='utf-8'
        )
