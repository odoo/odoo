from odoo import models


class AccountEdiXmlUblTr(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl.tr'

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
