from odoo import models


class AccountEdiXmlUbl_21(models.AbstractModel):
    _name = 'account.edi.xml.ubl_21'
    _inherit = ['account.edi.xml.ubl_20']
    _description = "UBL 2.1"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_21.xml"

    # -------------------------------------------------------------------------
    # EXPORT: Templates
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)

        if vals['document_type'] != 'invoice':
            # In UBL 2.1, Delivery, PaymentMeans, PaymentTerms exist also in DebitNote and CreditNote
            self._add_invoice_delivery_nodes(document_node, vals)
            self._add_invoice_payment_means_nodes(document_node, vals)
            self._add_invoice_payment_terms_nodes(document_node, vals)

        return document_node

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)

        invoice = vals['invoice']
        document_node.update({
            'cbc:UBLVersionID': {'_text': '2.1'},
            'cbc:DueDate': {'_text': invoice.invoice_date_due} if vals['document_type'] == 'invoice' else None,
            'cbc:CreditNoteTypeCode': {'_text': 261 if vals['process_type'] == 'selfbilling' else 381} if vals['document_type'] == 'credit_note' else None,
            'cbc:BuyerReference': {'_text': invoice.commercial_partner_id.ref},
        })

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        super()._add_document_allowance_charge_nodes(document_node, vals)

        # AllowanceCharge exists in debit notes only in UBL 2.1
        if vals['document_type'] == 'debit_note':
            document_node['cac:AllowanceCharge'] = []
            for base_line in vals['base_lines']:
                if self._is_document_allowance_charge(base_line):
                    document_node['cac:AllowanceCharge'].append(
                        self._get_document_allowance_charge_node({
                            **vals,
                            'base_line': base_line,
                        })
                    )

    def _add_invoice_line_period_nodes(self, line_node, vals):
        base_line = vals['base_line']

        # deferred_start_date & deferred_end_date are enterprise-only fields
        if (
            vals['document_type'] in {'invoice', 'credit_note'}
            and (base_line.get('deferred_start_date') or base_line.get('deferred_end_date'))
        ):
            line_node['cac:InvoicePeriod'] = {
                'cbc:StartDate': {'_text': base_line['deferred_start_date']},
                'cbc:EndDate': {'_text': base_line['deferred_end_date']},
            }

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        line_node['cac:AllowanceCharge'] = []
        if node := self._get_line_discount_allowance_charge_node(vals):
            line_node['cac:AllowanceCharge'].append(node)
        if vals['fixed_taxes_as_allowance_charges']:
            line_node['cac:AllowanceCharge'].extend(self._get_line_fixed_tax_allowance_charge_nodes(vals))
