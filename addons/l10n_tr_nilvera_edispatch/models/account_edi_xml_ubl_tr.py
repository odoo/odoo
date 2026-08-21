from odoo import models


class AccountEdiXmlUblTr(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl.tr'

    def _get_additional_document_reference_vals(self, invoice):
        additional_document_vals = super()._get_additional_document_reference_vals(invoice)

        if invoice._has_earchive_despatch_moves():
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

    def _l10n_tr_get_ecommerce_sale_additional_reference_data(self, invoice):
        ecom_data, ecom_errors = super()._l10n_tr_get_ecommerce_sale_additional_reference_data(invoice)

        # Delivery data
        if picking := invoice.l10n_tr_nilvera_edispatch_ids[:1]:
            carrier = picking.l10n_tr_nilvera_carrier_id or picking.l10n_tr_nilvera_driver_ids[0]
            if carrier.vat:
                transport_date = picking.date_done or picking.scheduled_date
                ecom_data.extend([
                    ('INT_TRANSPORTER', carrier.name),
                    ('INT_TRANSPORTER_REGISTER_NUMBER', carrier.vat),
                    ('INT_TRANSPORT_DATE', transport_date.strftime('%d.%m.%Y')),
                ])
            else:
                ecom_errors.append(self.env._("Carrier or driver VAT/TCKN is missing from the linked delivery."))
        return ecom_data, ecom_errors
