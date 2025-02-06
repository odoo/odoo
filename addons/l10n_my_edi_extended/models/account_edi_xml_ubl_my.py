# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class AccountEdiXmlUBLMyInvoisMY(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_myinvois_my"

    def _export_invoice_vals(self, invoice):
        # EXTENDS 'l10n_my_edi'
        vals = super()._export_invoice_vals(invoice)

        # For self billed documents (when sending in_xxx entries to the platform) the supplier and customer are unversed.
        if vals['vals']['document_type_code'] in ('11', '12', '13'):
            vals['vals']['accounting_supplier_party_vals']['party_vals'] = self._get_partner_party_vals(invoice.partner_id, role='supplier')
            vals['vals']['accounting_customer_party_vals']['party_vals'] = self._get_partner_party_vals(invoice.company_id.partner_id, role='customer')
            # /!\ For the company (regular invoices) it is the field on res.company that is used, and not the one on res.partner.
            # In master the behavior will be aligned and the classification information will be retrieved in _get_partner_party_vals
            vals['vals']['accounting_supplier_party_vals']['party_vals'].update({
                'industry_classification_code_attrs': {'name': invoice.partner_id.commercial_partner_id.l10n_my_edi_industrial_classification.name},
                'industry_classification_code': invoice.partner_id.commercial_partner_id.l10n_my_edi_industrial_classification.code,
            })
        return vals

    def _get_delivery_vals_list(self, invoice):
        # OVERRIDE 'l10n_my_edy'
        customer = invoice.company_id.partner_id if invoice.is_purchase_document() else invoice.partner_id
        return [{
            'accounting_delivery_party_vals': self._l10n_my_edi_get_delivery_party_vals(customer),
        }]

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS 'l10n_my_edi'
        constraints = super()._export_invoice_constraints(invoice, vals)
        # The credit/debit note error would trigger for self billed invoice, we check if it's the case and remove it if needed.
        document_type_code, original_document = self._l10n_my_edi_get_document_type_code(invoice)
        if document_type_code == '11' and f"myinvois_{invoice.id}_adjustment_origin" in constraints:
            del constraints[f'myinvois_{invoice.id}_adjustment_origin']
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
        # OVERRIDE 'l10n_my_edy'
        super()._l10n_my_edi_get_document_type_code(invoice)

        if 'debit_origin_id' in self.env['account.move']._fields and invoice.debit_origin_id:
            code = '03' if invoice.move_type == 'out_invoice' else '13'
            return code, invoice.debit_origin_id
        elif invoice.move_type in ('out_refund', 'in_refund'):
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
