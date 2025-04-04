from odoo import api, models, _


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_sa_edi_applicable(self, move):
        zatca_document = move.edi_document_ids.filtered(lambda d: d.edi_format_id.code == 'sa_zatca' and d.state == 'to_send')
        return move.country_code == 'SA' and move.move_type in ('out_invoice', 'out_refund') and zatca_document and move.state != 'draft'

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'sa_edi': {'label': _("Send to Zatca"), 'is_applicable': self._is_sa_edi_applicable}})
        return res

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        to_process = self.env['account.move']
        for invoice, invoice_data in invoices_data.items():
            if 'sa_edi' in invoice_data['extra_edis']:
                to_process |= invoice
        to_process.action_process_edi_web_services()
