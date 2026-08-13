from odoo import models


class AccountEdiXmlUblTr(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl.tr'

    def _get_additional_document_reference_vals(self, invoice):
        additional_document_vals = super()._get_additional_document_reference_vals(invoice)

        picking_ids = invoice._get_related_pickings()
        if picking_ids and picking_ids.filtered(lambda p: p.l10n_tr_nilvera_dispatch_type == 'IS_DESPATCH'):
            additional_document_vals.append({
                'cbc:ID': {'_text': '.'},
                'cbc:IssueDate': {'_text': invoice.invoice_date},
                'cbc:DocumentTypeCode': {'_text': 'IS_DESPATCH'},
            })
        return additional_document_vals

    def _get_dispatch_document_reference_vals(self, invoice):
        dispatch_document_vals = []
        for picking in invoice.l10n_tr_nilvera_edispatch_ids:
            dispatch_document_vals.append({
                'cbc:ID': {'_text': picking._get_nilvera_document_serial_number()},
                'cbc:IssueDate': {'_text': picking.scheduled_date.date()},
                'cbc:DocumentTypeCode': {'_text': 'SEVK'},
            })
        return dispatch_document_vals

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        document_node['cac:DespatchDocumentReference'] = self._get_dispatch_document_reference_vals(vals['invoice'])
