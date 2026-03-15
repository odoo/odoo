from lxml import etree

from odoo import models
from odoo.addons.account.tools import dict_to_xml


class PosEdiXmlUBL21(models.AbstractModel):
    _name = 'pos.edi.xml.ubl_21'
    _description = 'PoS Order UBL 2.1 builder'
    _inherit = ['account.edi.xml.ubl_21']

    def _export_pos_order(self, pos_order):
        vals = {'pos_order': pos_order.with_context(lang=pos_order.partner_id.lang)}
        document_node = self._get_pos_order_node(vals)

        errors = {constraint for constraint in self._export_pos_order_constraints(pos_order, vals).values() if constraint}

        template = self._get_document_template(vals)
        nsmap = self._get_document_nsmap(vals)

        xml_tree = dict_to_xml(document_node, nsmap=nsmap, template=template)
        return etree.tostring(xml_tree, xml_declaration=True, encoding='UTF-8'), set(errors)

    def _get_pos_order_node(self, vals):
        self._add_pos_order_config_vals(vals)
        self._add_pos_order_base_lines_vals(vals)
        self._add_pos_order_currency_vals(vals)
        self._add_pos_order_tax_grouping_function_vals(vals)
        self._add_pos_order_monetary_totals_vals(vals)

        document_node = {}
        self._add_pos_order_header_nodes(document_node, vals)
        self._add_pos_order_accounting_supplier_party_nodes(document_node, vals)
        self._add_pos_order_accounting_customer_party_nodes(document_node, vals)
        self._add_pos_order_payment_means_nodes(document_node, vals)

        self._add_pos_order_allowance_charge_nodes(document_node, vals)
        self._add_pos_order_tax_total_nodes(document_node, vals)
        self._add_pos_order_monetary_total_nodes(document_node, vals)
        self._add_pos_order_line_nodes(document_node, vals)
        return document_node

    def _add_pos_order_config_vals(self, vals):
        pos_order = vals['pos_order']
        supplier = pos_order.company_id.partner_id.commercial_partner_id
        customer = pos_order.partner_id

        vals.update({
            'document_type': 'invoice' if pos_order.amount_total >= 0 else 'credit_note',

            'company': pos_order.company_id,
            'journal': pos_order.config_id.invoice_journal_id,
            'name': pos_order.name,

            'supplier': supplier,
            'customer': customer,

            'currency_id': pos_order.currency_id,
            'company_currency_id': pos_order.company_id.currency_id,

            'use_company_currency': False,  # If true, use the company currency for the amounts instead of the invoice currency
            'fixed_taxes_as_allowance_charges': True,  # If true, include fixed taxes as AllowanceCharges on lines instead of as taxes
        })

    def _add_pos_order_base_lines_vals(self, vals):
        pos_order = vals['pos_order']

        base_lines = pos_order._prepare_tax_base_line_values()
        AccountTax = self.env['account.tax']
        AccountTax._add_tax_details_in_base_lines(base_lines, pos_order.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, pos_order.company_id)

        vals['base_lines'] = base_lines

    def _add_pos_order_currency_vals(self, vals):
        self._add_document_currency_vals(vals)

    def _add_pos_order_tax_grouping_function_vals(self, vals):
        self._add_document_tax_grouping_function_vals(vals)

    def _add_pos_order_monetary_totals_vals(self, vals):
        self._add_document_monetary_total_vals(vals)

    def _add_pos_order_header_nodes(self, document_node, vals):
        pos_order = vals['pos_order']
        document_node.update({
            'cbc:UBLVersionID': {'_text': '2.0'},
            'cbc:ID': {'_text': vals['name']},
            'cbc:IssueDate': {'_text': pos_order.date_order},
            'cbc:InvoiceTypeCode': {'_text': 380} if vals['document_type'] == 'invoice' else None,
            'cbc:Note': {'_text': pos_order.general_note},
            'cbc:DocumentCurrencyCode': {'_text': pos_order.currency_id.name},
            'cac:OrderReference': {
                'cbc:ID': {'_text': vals['name']},
            }
        })

    def _add_pos_order_accounting_supplier_party_nodes(self, document_node, vals):
        document_node['cac:AccountingSupplierParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'}),
        }

    def _add_pos_order_accounting_customer_party_nodes(self, document_node, vals):
        document_node['cac:AccountingCustomerParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'}),
        }

    def _add_pos_order_payment_means_nodes(self, document_node, vals):
        pass

    def _add_pos_order_allowance_charge_nodes(self, document_node, vals):
        self._add_document_allowance_charge_nodes(document_node, vals)

    def _add_pos_order_tax_total_nodes(self, document_node, vals):
        self._add_document_tax_total_nodes(document_node, vals)

    def _add_pos_order_monetary_total_nodes(self, document_node, vals):
        self._add_document_monetary_total_nodes(document_node, vals)
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        pos_order = vals['pos_order']
        total_included = vals[f'tax_exclusive_amount{vals["currency_suffix"]}']
        document_node[monetary_total_tag].update({
            'cbc:PrepaidAmount': {
                '_text': self.format_float(total_included - pos_order.amount_paid, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PayableAmount': {
                '_text': self.format_float(pos_order.amount_paid, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        })

    def _add_pos_order_line_nodes(self, document_node, vals):
        line_idx = 1

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[line_tag] = line_nodes = []
        for base_line in vals['base_lines']:
            # Only use product lines to generate the UBL InvoiceLines.
            # Other lines should be represented as AllowanceCharges.
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                line_node = self._get_pos_order_line_node(line_vals)
                line_nodes.append(line_node)
                line_idx += 1

    def _get_pos_order_line_node(self, vals):
        self._add_pos_order_line_vals(vals)

        line_node = {}
        self._add_pos_order_line_id_nodes(line_node, vals)
        self._add_pos_order_line_note_nodes(line_node, vals)
        self._add_pos_order_line_amount_nodes(line_node, vals)
        self._add_pos_order_line_period_nodes(line_node, vals)
        self._add_pos_order_line_allowance_charge_nodes(line_node, vals)
        self._add_pos_order_line_tax_total_nodes(line_node, vals)
        self._add_pos_order_line_item_nodes(line_node, vals)
        self._add_pos_order_line_tax_category_nodes(line_node, vals)
        self._add_pos_order_line_price_nodes(line_node, vals)
        return line_node

    def _add_pos_order_line_vals(self, vals):
        self._add_document_line_vals(vals)

    def _add_pos_order_line_id_nodes(self, line_node, vals):
        self._add_document_line_id_nodes(line_node, vals)

    def _add_pos_order_line_note_nodes(self, line_node, vals):
        self._add_document_line_note_nodes(line_node, vals)

    def _add_pos_order_line_amount_nodes(self, line_node, vals):
        self._add_document_line_amount_nodes(line_node, vals)

    def _add_pos_order_line_period_nodes(self, line_node, vals):
        pass

    def _add_pos_order_line_allowance_charge_nodes(self, line_node, vals):
        self._add_document_line_allowance_charge_nodes(line_node, vals)

    def _add_pos_order_line_tax_total_nodes(self, line_node, vals):
        self._add_document_line_tax_total_nodes(line_node, vals)

    def _add_pos_order_line_item_nodes(self, line_node, vals):
        self._add_document_line_item_nodes(line_node, vals)

        line = vals['base_line']['record']
        if line_name := line.name and line.name.replace('\n', ' '):
            line_node['cac:Item']['cbc:Description']['_text'] = line_name
            if not line_node['cac:Item']['cbc:Name']['_text']:
                line_node['cac:Item']['cbc:Name']['_text'] = line_name

    def _add_pos_order_line_tax_category_nodes(self, line_node, vals):
        self._add_document_line_tax_category_nodes(line_node, vals)

    def _add_pos_order_line_price_nodes(self, line_node, vals):
        self._add_document_line_price_nodes(line_node, vals)

    def _export_pos_order_constraints(self, pos_order, vals):
        return {}
