from datetime import timedelta
from lxml import etree
from pytz import timezone
import re

from odoo import api, fields, models
from odoo.addons.l10n_co_edi.models.account_invoice import L10N_CO_EDI_TYPE, DESCRIPTION_CREDIT_CODE
from odoo.addons.l10n_co_edi.models.res_partner import FINAL_CONSUMER_VAT


class PosEdiXmlUBLDian(models.AbstractModel):
    _name = 'pos.edi.xml.ubl_dian'
    _description = 'PoS Order DIAN UBL 2.1 builder'
    _inherit = ['account.edi.xml.ubl_dian', 'pos.edi.xml.ubl_21']

    @api.model
    def _export_filename(self, dian_sequence_str):
        suffix = re.sub(r'[\W_]', '', dian_sequence_str)
        return f'dian_{suffix}.xml'

    def _export_pos_order(self, pos_order):
        xml, errors = super()._export_pos_order(pos_order)

        root = etree.fromstring(xml)
        cert_sudo = pos_order.company_id.sudo().l10n_co_dian_certificate_ids[-1]
        self._dian_fill_signed_info_and_signature(root, cert_sudo)

        return etree.tostring(root, encoding='UTF-8'), errors

    def _get_pos_order_node(self, vals):
        document_node = super()._get_pos_order_node(vals)
        self._add_document_cufe_cude_cuds_vals(document_node, vals)
        self._add_document_uuid_node(document_node, vals)
        self._add_document_signature_vals(vals)
        self._add_document_extensions_node(document_node, vals)
        return document_node

    def _add_pos_order_config_vals(self, vals):
        super()._add_pos_order_config_vals(vals)

        pos_order = vals['pos_order']

        vals.update({
            'name': pos_order.l10n_co_edi_pos_name,
            'l10n_co_edi_type': pos_order._l10n_co_edi_type(),
            'l10n_co_edi_operation_type': pos_order._l10n_co_edi_operation_type(),
            'l10n_co_dian_identifier_type': pos_order._l10n_co_dian_identifier_type(),
            'l10n_co_edi_is_support_document': pos_order.l10n_co_edi_pos_journal_id.l10n_co_edi_is_support_document,
            'journal': pos_order.l10n_co_edi_pos_journal_id,
        })

        if not vals['customer']:
            # No partner selected -> default to Consumidor Final
            vals['customer'] = self.env.ref('l10n_co_edi.consumidor_final_customer')

        self._add_document_config_vals(vals)

    def _add_pos_order_base_lines_vals(self, vals):
        super()._add_pos_order_base_lines_vals(vals)

        for base_line in vals['base_lines']:
            self._transform_iva_withholding_base_amount(base_line)

        pos_order = vals['pos_order']
        if pos_order.is_tipped:
            tip_product = pos_order.config_id.tip_product_id
            for base_line in vals['base_lines']:
                if base_line['product_id'] == tip_product:
                    base_line['is_tip'] = True

    def _add_pos_order_header_nodes(self, document_node, vals):
        super()._add_pos_order_header_nodes(document_node, vals)
        self._add_document_header_nodes(document_node, vals)

        pos_order = vals['pos_order']

        post_datetime = pos_order.date_order.now(tz=timezone('America/Bogota'))

        document_node.update({
            'cbc:CustomizationID': {'_text': vals['l10n_co_edi_operation_type']},
            'cbc:ProfileID': {'_text': {
                'invoice': 'DIAN 2.1: Factura Electrónica de Venta',
                'credit_note': 'DIAN 2.1: Nota Crédito de Factura Electrónica de Venta',
                'debit_note': 'DIAN 2.1: Nota Débito de Factura Electrónica de Venta',
            }[vals['document_type']]},
            'cbc:IssueDate': {'_text': post_datetime.date().isoformat()},
            'cbc:IssueTime': {'_text': post_datetime.strftime("%H:%M:%S-05:00")},
            'cbc:InvoiceTypeCode': {'_text': '01'} if vals['document_type'] == 'invoice' else None,
            'cbc:CreditNoteTypeCode': {'_text': '91'} if vals['document_type'] == 'credit_note' else None,
        })

        if vals['document_type'] == 'credit_note':
            refund_order = pos_order.refunded_order_id
            refund_move = refund_order.account_move

            document_node['cac:DiscrepancyResponse'] = (
                {
                    'cbc:ReferenceID': {'_text': refund_move.name if refund_move else refund_order.name},
                    'cbc:ResponseCode': {'_text': '3'},
                    'cbc:Description': {'_text': next(value for key, value in DESCRIPTION_CREDIT_CODE if key == '3')}
                }
            )

            document_node['cac:BillingReference'] = (
                {
                    'cac:InvoiceDocumentReference': {
                        'cbc:ID': {'_text': refund_move.name if refund_move else refund_order.name},
                        'cbc:UUID': {
                            '_text': refund_move.l10n_co_edi_cufe_cude_ref if refund_move else refund_order.l10n_co_edi_pos_cufe_cude_ref,
                            'schemeName': "CUFE-SHA384",
                        },
                        'cbc:IssueDate': {'_text': refund_move.invoice_date.isoformat() if refund_move else refund_order.date_order.date().isoformat()},
                    },
                }
            )

        if vals['document_type'] != 'credit_note':
            document_node['cac:PrepaidPayment'] = [
                {
                    'cbc:ID': {'_text': p.name},
                    'cbc:PaidAmount': {
                        '_text': self.format_float(abs(p.amount), vals['currency_dp']),
                        'currencyID': vals['currency_id'].name,
                    },
                    'cbc:ReceivedDate': {'_text': p.payment_date.date().isoformat()},
                }
                for p in pos_order.payment_ids
            ]

    def _add_pos_order_accounting_supplier_party_nodes(self, document_node, vals):
        super()._add_pos_order_accounting_supplier_party_nodes(document_node, vals)
        document_node['cac:AccountingSupplierParty']['cbc:AdditionalAccountID'] = {
            '_text': vals['supplier']._l10n_co_edi_get_partner_type()
        }

    def _add_pos_order_accounting_customer_party_nodes(self, document_node, vals):
        super()._add_pos_order_accounting_customer_party_nodes(document_node, vals)
        document_node['cac:AccountingCustomerParty']['cbc:AdditionalAccountID'] = {
            '_text': vals['customer'].commercial_partner_id._l10n_co_edi_get_partner_type()
        }

    def _add_pos_order_payment_means_nodes(self, document_node, vals):
        pos_order = vals['pos_order']
        payment_option = pos_order.payment_ids.payment_method_id.l10n_co_edi_pos_payment_option_id

        document_node['cac:PaymentMeans'] = {
            'cbc:ID': {'_text': '1'},
            'cbc:PaymentMeansCode': {'_text': payment_option[0].code if payment_option else False},
            'cbc:PaymentDueDate': {'_text': fields.Date.to_string(pos_order.date_order)},
            'cbc:PaymentID': [
                {'_text': p.name}
                for p in pos_order.payment_ids
            ],
        }

    def _add_pos_order_monetary_total_nodes(self, document_node, vals):
        super()._add_pos_order_monetary_total_nodes(document_node, vals)
        pos_order = vals['pos_order']

        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        monetary_total_node = document_node[monetary_total_tag]
        monetary_total_node.update({
            'cbc:PayableAmount': {
                '_text': self.format_float(vals['tax_inclusive_amount'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PrepaidAmount': {
                '_text': self.format_float(abs(pos_order.amount_paid), vals['currency_dp']),
                'currencyID': vals['currency_id'].name,
            },
        })

    def _add_pos_order_line_item_nodes(self, line_node, vals):
        super()._add_pos_order_line_item_nodes(line_node, vals)

        line = vals['base_line']['record']
        product = vals['base_line']['product_id']

        description_parts = []
        if line.full_product_name:
            description_parts.append(line.full_product_name)
        else:
            description_parts.append(product.name)
        if product_description := product.description_sale:
            description_parts.append(product_description)

        line_node['cac:Item']['cbc:Description'] = {
            '_text': ' '.join(description_parts),
        }

    def _export_pos_order_constraints(self, pos_order, vals):
        # ANALOG _export_invoice_constraints in account.edi.xml.ubl_dian
        constraints = self._pos_order_constraints_common(vals)
        constraints.update({
            'ubl20_supplier_name_required': self._check_required_fields(vals['supplier'], 'name'),
            'ubl20_customer_name_required': self._check_required_fields(vals['customer'].commercial_partner_id, 'name'),
            'ubl20_invoice_name_required': self._check_required_fields(pos_order, 'name'),
            'ubl20_invoice_date_required': self._check_required_fields(pos_order, 'date_order'),
        })

        now = fields.Datetime.now()
        oldest_date = now - timedelta(days=5)
        newest_date = now + timedelta(days=10)
        if not (oldest_date <= fields.Datetime.to_datetime(pos_order.date_order) <= newest_date):
            constraints['dian_date'] = self.env._("The issue date can not be older than 5 days or more than 5 days in the future.")

        # required fields on pos_order
        if not pos_order.date_order:
            constraints['date_order'] = self.env._("The date of the order is required to compute the CUFE/CUDE/CUDS.")

        # required fields on company
        company = pos_order.company_id
        operation_mode = vals['l10n_co_dian_operation_mode']

        if not operation_mode:
            constraints['dian_operation_modes'] = self.env._("No DIAN Operation Mode Matches")
        else:
            mandatory_fields = ['dian_software_id', 'dian_software_operation_mode', 'dian_software_security_code']
            if company.l10n_co_dian_test_environment:
                mandatory_fields.append('dian_testing_id')
            for field in mandatory_fields:
                constraints[field] = self._check_required_fields(operation_mode, field)
            if vals['l10n_co_dian_identifier_type'] == 'cude' and not operation_mode.dian_software_security_code:
                constraints['l10n_co_dian_identifier_type'] = self.env._("The software PIN is required to compute the CUDE/CUDS.")

        # required fields on journal
        journal = vals['journal']
        if not pos_order._l10n_co_edi_is_refund() and not journal.l10n_co_dian_technical_key:
            constraints['l10n_co_dian_technical_key'] = self.env._("A technical key on the journal is required to compute the CUFE.")

        for field in ('l10n_co_edi_dian_authorization_number', 'l10n_co_edi_dian_authorization_date',
                      'l10n_co_edi_dian_authorization_end_date', 'l10n_co_edi_min_range_number',
                      'l10n_co_edi_max_range_number', 'l10n_co_dian_technical_key'):
            constraints[f"dian_{field}"] = self._check_required_fields(journal, field)

        # fields on partners
        for role in ('customer', 'supplier'):
            commercial_partner = vals[role].commercial_partner_id
            constraints.update({
                f"dian_vat_{role}": self._check_required_fields(commercial_partner, 'vat'),
                f"dian_identification_type_{role}": self._check_required_fields(commercial_partner, 'l10n_latam_identification_type_id'),
                f"dian_obligation_type_{role}": self._check_required_fields(commercial_partner, 'l10n_co_edi_obligation_type_ids'),
            })
            if commercial_partner.l10n_latam_identification_type_id.l10n_co_document_code != 'rut' and commercial_partner.vat and '-' in commercial_partner.vat:
                constraints[f"dian_NIT_{role}"] = self.env._("The identification number of %(partner)s contains '-' but is not a NIT.", partner=commercial_partner.name)
            if vals[role].country_code == 'CO' and commercial_partner.vat != FINAL_CONSUMER_VAT:
                constraints[f'dian_country_subentity_{role}'] = self._check_required_fields(vals[role], 'state_id')
                constraints[f"dian_city_{role}"] = self._check_required_fields(vals[role], 'city_id')

        # fields on lines
        for line in pos_order.lines:
            product = line.product_id
            constraints[f"product_{product.id}"] = self._check_required_fields(product, ['default_code', 'barcode', 'unspsc_code_id'])

            if vals['l10n_co_edi_type'] == L10N_CO_EDI_TYPE['Export Invoice'] and product:
                if not product.l10n_co_edi_customs_code:
                    constraints['dian_export_product_code'] = self.env._("Every exportation product must have a customs code.")
                if not product.l10n_co_edi_brand:
                    constraints['dian_export_product_brand'] = self.env._("Every exportation product must have a brand.")

            if "IBUA" in line.tax_ids.l10n_co_edi_type.mapped('name') and product.l10n_co_edi_ref_nominal_tax == 0:
                constraints['dian_sugar'] = self.env._(
                    "'Volume in milliliters' should be set on product: %s when using IBUA taxes.", line.product_id.name)

            if not self._dian_get_co_ubl_code(line.product_uom_id):
                constraints['dian_uom'] = self.env._("There is no Colombian code on the unit of measure: %s", line.product_uom_id.name)

        if vals['l10n_co_edi_operation_type'] == '20':
            if not pos_order.refunded_order_id:
                constraints['dian_credit_note'] = self.env._("There is no refund order linked to this pos order but the operation type is '20'.")
            elif not pos_order.refunded_order_id.l10n_co_edi_pos_cufe_cude_ref and not pos_order.refunded_order_id.to_invoice:
                constraints['dian_credit_note_cufe'] = self.env._("The linked refund order has no CUFE.")

        # payment option
        payment_option = pos_order.payment_ids.payment_method_id.l10n_co_edi_pos_payment_option_id
        if not payment_option:
            constraints['dian_payment_option'] = self.env._("'Payment Option' is required on a payment method")

        return constraints

    def _pos_order_constraints_common(self, vals):
        # ANALOG _invoice_constraints_common in account.edi.xml.ubl_20
        return self._constraints_common(vals)

    @api.model
    def _constraints_common(self, vals):
        for base_line in vals['base_lines']:
            if not self._is_document_allowance_charge(base_line) and not base_line['tax_ids']:
                return {'tax_on_line': self.env._("Each order line should have at least one tax.")}
        return {}
