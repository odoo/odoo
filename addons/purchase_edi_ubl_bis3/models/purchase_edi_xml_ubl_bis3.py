from lxml import etree

from odoo import models, Command, _
from odoo.tools import html2plaintext
from odoo.addons.account_edi_ubl_cii.tools import Order
from odoo.addons.account.tools import dict_to_xml


class PurchaseEdiXmlUbl_Bis3(models.AbstractModel):
    _name = 'purchase.edi.xml.ubl_bis3'
    _inherit = ['account.edi.xml.ubl_bis3']
    _description = "Purchase UBL BIS Ordering 3.5"

    # -------------------------------------------------------------------------
    # Purchase Order EDI Export
    # -------------------------------------------------------------------------

    def _export_order(self, purchase_order):
        vals = {'purchase_order': purchase_order}
        document_node = self._get_purchase_order_node(vals)
        xml_content = dict_to_xml(document_node, template=Order, nsmap=self._get_document_nsmap(vals))
        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8')

    def _get_purchase_order_node(self, vals):
        self._add_purchase_order_config_vals(vals)
        self._add_purchase_order_base_lines_vals(vals)
        self._add_purchase_order_currency_vals(vals)
        self._add_purchase_order_tax_grouping_function_vals(vals)
        self._add_purchase_order_monetary_totals_vals(vals)

        document_node = {}
        self._add_purchase_order_header_nodes(document_node, vals)
        self._add_purchase_order_buyer_customer_party_nodes(document_node, vals)
        self._add_purchase_order_seller_supplier_party_nodes(document_node, vals)
        self._add_purchase_order_delivery_nodes(document_node, vals)
        self._add_purchase_order_payment_terms_nodes(document_node, vals)
        self._add_purchase_order_allowance_charge_nodes(document_node, vals)
        self._add_purchase_order_tax_total_nodes(document_node, vals)
        self._add_purchase_order_monetary_total_nodes(document_node, vals)
        self._add_purchase_order_line_nodes(document_node, vals)
        return document_node

    def _add_purchase_order_config_vals(self, vals):
        purchase_order = vals['purchase_order']
        supplier = purchase_order.partner_id
        customer = purchase_order.company_id.partner_id.commercial_partner_id

        customer_delivery_address = customer.child_ids.filtered(lambda child: child.type == 'delivery')
        partner_shipping = (
            purchase_order.dest_address_id
            or (customer_delivery_address and customer_delivery_address[0])
            or customer
        )

        vals.update({
            'document_type': 'order',

            'supplier': supplier,
            'customer': customer,
            'partner_shipping': partner_shipping,

            'currency_id': purchase_order.currency_id,
            'company_currency_id': purchase_order.company_id.currency_id,

            'use_company_currency': False,  # If true, use the company currency for the amounts instead of the order currency
            'fixed_taxes_as_allowance_charges': True,  # If true, include fixed taxes as AllowanceCharges on lines instead of as taxes
        })

    def _add_purchase_order_base_lines_vals(self, vals):
        purchase_order = vals['purchase_order']
        AccountTax = self.env['account.tax']

        base_lines = [line._prepare_base_line_for_taxes_computation() for line in purchase_order.order_line.filtered(lambda line: not line.display_type)]
        AccountTax._add_tax_details_in_base_lines(base_lines, purchase_order.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, purchase_order.company_id)

        vals['base_lines'] = base_lines

    def _add_purchase_order_currency_vals(self, vals):
        self._add_document_currency_vals(vals)

    def _add_purchase_order_tax_grouping_function_vals(self, vals):
        self._add_document_tax_grouping_function_vals(vals)

    def _add_purchase_order_monetary_totals_vals(self, vals):
        self._add_document_monetary_total_vals(vals)

    def _add_purchase_order_header_nodes(self, document_node, vals):
        purchase_order = vals['purchase_order']
        document_node.update({
            'cbc:CustomizationID': {'_text': 'urn:fdc:peppol.eu:poacc:trns:order:3'},
            'cbc:ProfileID': {'_text': 'urn:fdc:peppol.eu:poacc:bis:ordering:3'},
            'cbc:ID': {'_text': purchase_order.name},
            'cbc:IssueDate': {'_text': purchase_order.create_date.date()},
            'cbc:OrderTypeCode': {'_text': '105'},
            'cbc:Note': {'_text': html2plaintext(purchase_order.note)} if purchase_order.note else None,
            'cbc:DocumentCurrencyCode': {'_text': vals['currency_name']},
            'cac:QuotationDocumentReference': {
                'cbc:ID': {'_text': purchase_order.partner_ref}
            },
        })

    def _add_purchase_order_buyer_customer_party_nodes(self, document_node, vals):
        document_node['cac:BuyerCustomerParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'})
        }

    def _add_purchase_order_seller_supplier_party_nodes(self, document_node, vals):
        document_node['cac:SellerSupplierParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'})
        }

    def _add_purchase_order_delivery_nodes(self, document_node, vals):
        document_node['cac:Delivery'] = {
            'cac:DeliveryParty': self._get_party_node({**vals, 'partner': vals['partner_shipping'], 'role': 'delivery'})
        }

    def _add_purchase_order_payment_terms_nodes(self, document_node, vals):
        purchase_order = vals['purchase_order']
        if purchase_order.payment_term_id:
            document_node['cac:PaymentTerms'] = {
                'cbc:Note': {'_text': purchase_order.payment_term_id.name}
            }

    def _add_purchase_order_allowance_charge_nodes(self, document_node, vals):
        self._add_document_allowance_charge_nodes(document_node, vals)

    def _add_purchase_order_tax_total_nodes(self, document_node, vals):
        self._add_document_tax_total_nodes(document_node, vals)

    def _add_purchase_order_monetary_total_nodes(self, document_node, vals):
        self._add_document_monetary_total_nodes(document_node, vals)

    def _add_purchase_order_line_nodes(self, document_node, vals):
        line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[line_tag] = order_line_nodes = []

        line_idx = 1
        for base_line in vals['base_lines']:
            line_vals = {
                **vals,
                'line_idx': line_idx,
                'base_line': base_line,
            }
            self._add_purchase_order_line_vals(line_vals)

            line_node = {}
            self._add_purchase_order_line_id_nodes(line_node, line_vals)
            self._add_purchase_order_line_amount_nodes(line_node, line_vals)
            self._add_purchase_order_line_allowance_charge_nodes(line_node, line_vals)
            self._add_purchase_order_line_tax_total_nodes(line_node, line_vals)
            self._add_purchase_order_line_item_nodes(line_node, line_vals)
            self._add_purchase_order_line_tax_category_nodes(line_node, line_vals)
            self._add_purchase_order_line_price_nodes(line_node, line_vals)

            order_line_nodes.append({
                'cac:LineItem': line_node,
            })
            line_idx += 1

    def _add_purchase_order_line_vals(self, vals):
        self._add_document_line_vals(vals)

    def _add_purchase_order_line_id_nodes(self, line_node, vals):
        self._add_document_line_id_nodes(line_node, vals)

    def _add_purchase_order_line_amount_nodes(self, line_node, vals):
        self._add_document_line_amount_nodes(line_node, vals)

    def _add_purchase_order_line_allowance_charge_nodes(self, line_node, vals):
        self._add_document_line_allowance_charge_nodes(line_node, vals)

    def _add_purchase_order_line_tax_total_nodes(self, line_node, vals):
        self._add_document_line_tax_total_nodes(line_node, vals)

    def _add_purchase_order_line_tax_category_nodes(self, line_node, vals):
        self._add_document_line_tax_category_nodes(line_node, vals)

    def _add_purchase_order_line_item_nodes(self, line_node, vals):
        self._add_document_line_item_nodes(line_node, vals)

        line_item_node = line_node['cac:Item']
        order_line = vals['base_line']['record']
        product = order_line.product_id
        order = order_line.order_id
        supplier_info = product.variant_seller_ids.filtered(lambda s:
            s.partner_id == order.partner_id
            and (
                s.product_id == product
                or (not s.product_id and s.product_tmpl_id == product.product_tmpl_id)
            ) and (s.product_code or s.product_name),
        )[:1]

        # Prefer the seller's product name over our (buyer) product name
        if supplier_info.product_name:
            line_item_node['cbc:Name']['_text'] = supplier_info.product_name

        # When generating purchase order (PO) we are not considered as the seller of the sale but
        # buyer. The `SellersItemIdentification` is therefore the PO's partner product ID.
        line_item_node['cac:SellersItemIdentification']['cbc:ID'] = {
            '_text': supplier_info.product_code,
        }

        if line_name := order_line.name and order_line.name.replace('\n', ' '):
            line_item_node['cbc:Description'] = {'_text': line_name}

    def _add_purchase_order_line_price_nodes(self, line_node, vals):
        self._add_document_line_price_nodes(line_node, vals)

    # -------------------------------------------------------------------------
    # Purchase Order EDI Import
    # -------------------------------------------------------------------------

    def _retrieve_order_vals(self, order, tree):
        """ Fill order details by extracting details from xml tree.
        param order: Order to fill details from xml tree.
        param tree: Xml tree to extract details.
        :return: list of logs to add warning and information about data from xml.
        """
        order_vals, logs = super()._retrieve_order_vals(order, tree)
        partner, partner_logs = self._import_partner(
            order.company_id,
            **self._import_retrieve_partner_vals(tree, 'SellerSupplier'),
        )
        if partner:
            order_vals['partner_id'] = partner.id
        order_vals['partner_ref'] = tree.findtext('./{*}ID')
        order_vals['origin'] = tree.findtext('./{*}OriginatorDocumentReference/{*}ID')

        delivery_partner, delivery_logs = self._import_partner(
            order.company_id,
            **self._import_retrieve_partner_vals(tree, 'Delivery'),
        )
        if delivery_partner:
            order_vals['dest_address_id'] = delivery_partner.id

        allowance_charges_line_vals, allowance_charges_logs = self._import_document_allowance_charges(tree, order, 'purchase')
        lines_vals, line_logs = self._import_lines(order, tree, './{*}OrderLine/{*}LineItem', document_type='order', tax_type='purchase')
        # adapt each line to purchase.order.line
        for line in lines_vals:
            line['product_qty'] = line.pop('quantity')
            # remove invoice line fields
            line.pop('deferred_start_date', False)
            line.pop('deferred_end_date', False)
            if not line.get('product_id'):
                line_logs.append(_("Could not retrieve the product named: %(name)s", name=line['name']))
        lines_vals += allowance_charges_line_vals

        # Update order with lines excluding discounts
        order_vals['order_line'] = [Command.create(line_vals) for line_vals in lines_vals]
        logs += partner_logs + delivery_logs + line_logs + allowance_charges_logs

        return order_vals, logs
