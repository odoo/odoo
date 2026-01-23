from odoo import _, models
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt
from odoo.addons.account_edi_ubl_cii.tools import Invoice, CreditNote, DebitNote
from odoo.tools import frozendict, html2plaintext


class AccountEdiUBLInvoiceCommon(models.AbstractModel):
    _name = "account.edi.ubl.invoice_common"
    _inherit = 'account.edi.ubl'
    _description = "Base helpers for UBL Invoice Common"

    def _ubl_add_id_node(self, vals):
        # EXTENDS
        super()._ubl_add_id_node(vals)
        vals['document_node']['cbc:ID']['_text'] = vals['invoice'].name

    def _ubl_add_issue_date_node(self, vals):
        # EXTENDS
        super()._ubl_add_issue_date_node(vals)
        vals['document_node']['cbc:IssueDate']['_text'] = vals['invoice'].invoice_date

    def _ubl_add_notes_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_notes_nodes(vals)

        invoice = vals['invoice']
        terms_and_condition = html2plaintext(invoice.narration) if invoice.narration else None
        if terms_and_condition:
            vals['document_node']['cbc:Note'].append({'_text': terms_and_condition})

    def _ubl_add_line_period_nodes(self, vals):
        # EXTENDS
        super()._ubl_add_line_period_nodes(vals)
        base_line = vals['line_vals']['base_line']
        invoice_period_nodes = vals['line_node']['cac:InvoicePeriod']

        if base_line.get('deferred_start_date') or base_line.get('deferred_end_date'):
            invoice_period_nodes.append({
                'cbc:StartDate': {'_text': base_line['deferred_start_date']},
                'cbc:EndDate': {'_text': base_line['deferred_end_date']},
            })

    def _ubl_add_order_reference_node(self, vals):
        # EXTENDS
        super()._ubl_add_order_reference_node(vals)

        invoice = vals['invoice']
        order_ref_node = vals['document_node']['cac:OrderReference']
        order_ref_node['cbc:ID']['_text'] = invoice.ref or invoice.name

        if vals['module_installed']('sale'):
            so_names = set(invoice.invoice_line_ids.sale_line_ids.order_id.mapped('name'))
            if so_names:
                order_ref_node['cbc:SalesOrderID']['_text'] = ",".join(so_names)

    def _ubl_get_delivery_node_from_delivery_address(self, vals):
        # EXTENDS
        node = super()._ubl_get_delivery_node_from_delivery_address(vals)
        invoice = vals['invoice']

        if invoice.delivery_date:
            node['cbc:ActualDeliveryDate']['_text'] = invoice.delivery_date
        return node

    def _ubl_add_legal_monetary_total_prepaid_payable_amount_node(self, vals, in_foreign_currency=True):
        # EXTENDS
        super()._ubl_add_legal_monetary_total_prepaid_payable_amount_node(vals, in_foreign_currency=in_foreign_currency)
        invoice = vals['invoice']
        currency = vals['currency_id'] if in_foreign_currency else vals['company_currency']
        node = vals['legal_monetary_total_node']

        if in_foreign_currency:
            amount_total = invoice.amount_total
            amount_residual = invoice.amount_residual
        else:
            amount_total = invoice.amount_total_signed * -invoice.direction_sign
            amount_residual = invoice.amount_residual_signed * -invoice.direction_sign

        node['cbc:PrepaidAmount']['_text'] += amount_total - amount_residual
        node['cbc:PayableAmount']['_text'] = FloatFmt(
            amount_residual,
            min_dp=currency.decimal_places,
        )

    # -------------------------------------------------------------------------
    # EXPORT: Preparing values
    # -------------------------------------------------------------------------

    def _export_invoice_prepare_values(self, vals, invoice):
        vals['invoice'] = invoice

        vals['_ubl_values'] = {}
        vals['base_lines'], vals['tax_lines'] = invoice._get_rounded_base_and_tax_lines()
        for base_line in vals['base_lines']:
            base_line['_ubl_values'] = {}

class AccountEdiUBLInvoice(models.AbstractModel):
    _name = "account.edi.ubl.invoice"
    _inherit = 'account.edi.ubl.invoice_common'
    _description = "Base helpers for UBL Invoice"

    def _ubl_init_values(self):
        # EXTENDS
        ubl_values = super()._ubl_init_values()
        ubl_values['nsmap'][None] = 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2'
        return ubl_values

    def _ubl_add_due_date_node(self, vals):
        # EXTENDS
        super()._ubl_add_due_date_node(vals)
        vals['document_node']['cbc:DueDate']['_text'] = vals['invoice'].invoice_date_due

    def _ubl_add_invoice_type_code_node(self, vals):
        # EXTENDS
        super()._ubl_add_invoice_type_code_node(vals)
        vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 380

    def _ubl_add_legal_monetary_total_node(self, vals):
        # EXTENDS
        super()._ubl_add_legal_monetary_total_node(vals)
        node = vals['document_node']['cac:LegalMonetaryTotal']
        sub_vals = {**vals, 'legal_monetary_total_node': node}
        self._ubl_add_legal_monetary_total_line_extension_amount_node(sub_vals, 'cac:InvoiceLine')
        self._ubl_add_legal_monetary_total_tax_exclusive_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_tax_inclusive_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_allowance_charge_total_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_payable_rounding_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_prepaid_payable_amount_node(sub_vals)

    def _ubl_get_invoice_node(self, vals):
        document_node = {
            '_nsmap': vals['nsmap'],
            '_template': Invoice,
        }
        sub_vals = {**vals, 'document_node': document_node}
        self._ubl_add_version_id_node(sub_vals)
        self._ubl_add_customization_id_node(sub_vals)
        self._ubl_add_profile_id_node(sub_vals)
        self._ubl_add_id_node(sub_vals)
        self._ubl_add_issue_date_node(sub_vals)
        self._ubl_add_due_date_node(sub_vals)
        self._ubl_add_invoice_type_code_node(sub_vals)
        self._ubl_add_notes_nodes(sub_vals)
        self._ubl_add_document_currency_code_node(sub_vals)
        self._ubl_add_tax_currency_code_node(sub_vals)
        self._ubl_add_order_reference_node(sub_vals)
        self._ubl_add_accounting_supplier_party_node(sub_vals)
        self._ubl_add_accounting_customer_party_node(sub_vals)
        self._ubl_add_invoice_delivery_nodes(sub_vals)
        self._ubl_add_payment_means_nodes(sub_vals)
        self._ubl_add_payment_terms_nodes(sub_vals)
        self._ubl_add_allowance_charge_nodes(sub_vals)
        self._ubl_add_tax_totals_nodes(sub_vals)
        self._ubl_add_invoice_line_nodes(sub_vals)
        self._ubl_add_legal_monetary_total_node(sub_vals)
        return document_node

class AccountEdiUBLCreditNote(models.AbstractModel):
    _name = "account.edi.ubl.credit_note"
    _inherit = 'account.edi.ubl.invoice_common'
    _description = "Base helpers for UBL Credit Note"

    def _ubl_init_values(self):
        # EXTENDS
        ubl_values = super()._ubl_init_values()
        ubl_values['nsmap'][None] = 'urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2'
        return ubl_values

    def _ubl_add_credit_note_type_code_node(self, vals):
        # EXTENDS
        super()._ubl_add_credit_note_type_code_node(vals)
        vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 381

    def _ubl_add_legal_monetary_total_node(self, vals):
        # EXTENDS
        super()._ubl_add_legal_monetary_total_node(vals)
        node = vals['document_node']['cac:LegalMonetaryTotal']
        sub_vals = {**vals, 'legal_monetary_total_node': node}
        self._ubl_add_legal_monetary_total_line_extension_amount_node(sub_vals, 'cac:CreditNoteLine')
        self._ubl_add_legal_monetary_total_tax_exclusive_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_tax_inclusive_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_allowance_charge_total_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_payable_rounding_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_prepaid_payable_amount_node(sub_vals)

    def _ubl_get_credit_note_node(self, vals):
        document_node = {
            '_nsmap': vals['nsmap'],
            '_template': CreditNote,
        }
        sub_vals = {**vals, 'document_node': document_node}
        self._ubl_add_version_id_node(sub_vals)
        self._ubl_add_customization_id_node(sub_vals)
        self._ubl_add_profile_id_node(sub_vals)
        self._ubl_add_id_node(sub_vals)
        self._ubl_add_issue_date_node(sub_vals)
        self._ubl_add_credit_note_type_code_node(sub_vals)
        self._ubl_add_notes_nodes(sub_vals)
        self._ubl_add_document_currency_code_node(sub_vals)
        self._ubl_add_tax_currency_code_node(sub_vals)
        self._ubl_add_order_reference_node(sub_vals)
        self._ubl_add_accounting_supplier_party_node(sub_vals)
        self._ubl_add_accounting_customer_party_node(sub_vals)
        self._ubl_add_invoice_delivery_nodes(sub_vals)
        self._ubl_add_payment_means_nodes(sub_vals)
        self._ubl_add_payment_terms_nodes(sub_vals)
        self._ubl_add_allowance_charge_nodes(sub_vals)
        self._ubl_add_tax_totals_nodes(sub_vals)
        self._ubl_add_credit_note_line_nodes(sub_vals)
        self._ubl_add_legal_monetary_total_node(sub_vals)
        return document_node

class AccountEdiUBLDebitNote(models.AbstractModel):
    _name = "account.edi.ubl.debit_note"
    _inherit = 'account.edi.ubl.invoice_common'
    _description = "Base helpers for UBL Debit Note"

    def _ubl_init_values(self):
        # EXTENDS
        ubl_values = super()._ubl_init_values()
        ubl_values['nsmap'][None] = 'urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2'
        return ubl_values

    def _ubl_add_requested_monetary_total_node(self, vals):
        # EXTENDS
        super()._ubl_add_requested_monetary_total_node(vals)
        node = vals['document_node']['cac:RequestedMonetaryTotal']
        sub_vals = {**vals, 'legal_monetary_total_node': node}
        self._ubl_add_legal_monetary_total_line_extension_amount_node(sub_vals, 'cac:DebitNoteLine')
        self._ubl_add_legal_monetary_total_tax_exclusive_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_tax_inclusive_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_allowance_charge_total_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_payable_rounding_amount_node(sub_vals)
        self._ubl_add_legal_monetary_total_prepaid_payable_amount_node(sub_vals)

    def _ubl_get_debit_note_node(self, vals):
        document_node = {
            '_nsmap': vals['nsmap'],
            '_template': DebitNote,
        }
        sub_vals = {**vals, 'document_node': document_node}
        self._ubl_add_version_id_node(sub_vals)
        self._ubl_add_customization_id_node(sub_vals)
        self._ubl_add_profile_id_node(sub_vals)
        self._ubl_add_id_node(sub_vals)
        self._ubl_add_issue_date_node(sub_vals)
        self._ubl_add_notes_nodes(sub_vals)
        self._ubl_add_document_currency_code_node(sub_vals)
        self._ubl_add_tax_currency_code_node(sub_vals)
        self._ubl_add_order_reference_node(sub_vals)
        self._ubl_add_accounting_supplier_party_node(sub_vals)
        self._ubl_add_accounting_customer_party_node(sub_vals)
        self._ubl_add_invoice_delivery_nodes(sub_vals)
        self._ubl_add_payment_means_nodes(sub_vals)
        self._ubl_add_payment_terms_nodes(sub_vals)
        self._ubl_add_allowance_charge_nodes(sub_vals)
        self._ubl_add_tax_totals_nodes(sub_vals)
        self._ubl_add_debit_note_line_nodes(sub_vals)
        self._ubl_add_requested_monetary_total_node(sub_vals)
        return document_node
