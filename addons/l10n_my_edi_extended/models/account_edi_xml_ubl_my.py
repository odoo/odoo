# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountEdiXmlUBLMyInvoisMY(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_myinvois_my"

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'l10n_my_edi'
        vals = super()._export_invoice_vals(invoice)

        # For self billed documents (when sending in_xxx entries to the platform) the supplier and customer are reversed.
        if self._is_self_billed(vals['vals']['document_type_code']):
            vals['vals']['accounting_supplier_party_vals']['party_vals'] = self._get_partner_party_vals(invoice.partner_id, role='supplier')
            vals['vals']['accounting_customer_party_vals']['party_vals'] = self._get_partner_party_vals(invoice.company_id.partner_id, role='customer')
            # /!\ For the company (regular invoices) it is the field on res.company that is used, and not the one on res.partner.
            # In master the behavior will be aligned and the classification information will be retrieved in _get_partner_party_vals
            vals['vals']['accounting_supplier_party_vals']['party_vals'].update({
                'industry_classification_code_attrs': {'name': invoice.partner_id.commercial_partner_id.l10n_my_edi_industrial_classification.name},
                'industry_classification_code': invoice.partner_id.commercial_partner_id.l10n_my_edi_industrial_classification.code,
            })
            # Self-billed invoices must use the number given by the supplier.
            if invoice.ref:
                vals['vals']['id'] = invoice.ref
        # Sometimes, a foreign customer is also a supplier.
        # To avoid needing to change the Generic TIN depending on what you do with your commercial partner, we will automatically switch
        # depending on the context.
        if self._is_self_billed(vals['vals']['document_type_code']):
            other_party = vals["vals"]["accounting_supplier_party_vals"]["party_vals"]
            opposite_generic_tin = 'EI00000000020'
            expected_generic_tin = 'EI00000000030'
        else:
            other_party = vals["vals"]["accounting_customer_party_vals"]["party_vals"]
            opposite_generic_tin = 'EI00000000030'
            expected_generic_tin = 'EI00000000020'
        # Switch the generic tin to the correct one when it makes sense (For example when a supplier has the buyer generic tin set)
        for identification_val in other_party['party_identification_vals']:
            if identification_val.get('id_attrs', {}).get('schemeID') == 'TIN' and identification_val.get('id') == opposite_generic_tin:
                identification_val['id'] = expected_generic_tin
        return vals

    def _get_delivery_vals_list(self, invoice):
        # OVERRIDE 'l10n_my_edi'
        customer = invoice.company_id.partner_id if invoice.is_purchase_document() else invoice.partner_id
        return [{
            'accounting_delivery_party_vals': self._l10n_my_edi_get_delivery_party_vals(customer),
        }]

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'l10n_my_edi'
        constraints = super()._export_invoice_constraints(invoice, vals)
        # The classification check was only looking at the product, we also want to validate lines without product
        for line in invoice.invoice_line_ids.filtered(lambda line: line.display_type not in ('line_note', 'line_section')):
            # If there are no products, we still expect a classification to be manually set.
            if not line.product_id and not line.l10n_my_edi_classification_code:
                self._l10n_my_edi_make_validation_error(constraints, 'class_code_required_line', line.id, line.display_name)
            # We allow invoicing a product with no classification when the classification has been manually provided.
            if f"myinvois_{line.product_id.id}_class_code_required" in constraints and line.l10n_my_edi_classification_code:
                del constraints[f"myinvois_{line.product_id.id}_class_code_required"]

        return constraints

    @api.model
    def _l10n_my_edi_get_document_type_code(self, invoice):
        """ Override the super method to include self billed documents. """
        # OVERRIDE 'l10n_my_edi'
        super()._l10n_my_edi_get_document_type_code(invoice)

        if 'debit_origin_id' in self.env['account.move']._fields and invoice.debit_origin_id:
            code = '03' if invoice.move_type == 'out_invoice' else '13'
            return code, invoice.debit_origin_id
        elif invoice.move_type in ('out_refund', 'in_refund'):
            # We consider a credit note a refund if it is paid and fully reconciled with a payment or bank transaction.
            payment_terms = invoice.line_ids.filtered(lambda aml: aml.display_type == 'payment_term')
            counterpart_amls = payment_terms.matched_debit_ids.debit_move_id + payment_terms.matched_credit_ids.credit_move_id
            counterpart_move_type = 'out_invoice' if invoice.move_type == 'out_refund' else 'out_refund'
            has_payments = bool(counterpart_amls.move_id.filtered(lambda move: move.move_type != counterpart_move_type))
            is_paid = invoice.payment_state in ('in_payment', 'paid', 'reversed')
            if is_paid and has_payments:
                code = '04' if invoice.move_type == 'out_refund' else '14'
            else:
                code = '02' if invoice.move_type == 'out_refund' else '12'

            return code, invoice.reversed_entry_id
        else:
            code = '01' if invoice.move_type == 'out_invoice' else '11'
            return code, None

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # EXTENDS 'l10n_my_edi' to use the new field
        vals = super()._get_invoice_line_item_vals(line, taxes_vals)
        # Replace the code to get it from the line instead
        vals['commodity_classification_vals'] = [{
            'item_classification_code': line.l10n_my_edi_classification_code,
            'item_classification_attrs': {'listID': 'CLASS'},
        }]
        return vals

    @api.model
    def _is_self_billed(self, document_code):
        """ Small helper which returns True if a document code is for self billing.
        To avoid repeating the check multiple time, risking to forget to update one or the other.
        """
        return document_code in {"11", "12", "13", "14"}
