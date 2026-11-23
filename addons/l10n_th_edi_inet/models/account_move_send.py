# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.exceptions import UserError


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_th_edi_inet_applicable(self, move):
        return bool(
            move.company_id.sudo().l10n_th_edi_inet_authorization_code
            and 'ready_to_send' in (move.l10n_th_edi_state, *move.l10n_th_tax_invoice_ids.mapped('l10n_th_edi_state')),
        )

    def _get_all_extra_edis(self):
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res['th_inet_send'] = {'label': self.env._("Send to INET"), 'is_applicable': self._is_th_edi_inet_applicable}
        return res

    @api.model
    def _get_invoice_extra_attachments(self, move):
        # EXTENDS 'account'
        tax_invoices = move.l10n_th_tax_invoice_ids
        return (
            super()._get_invoice_extra_attachments(move)
            + move.l10n_th_edi_xml_file_id
            + move.l10n_th_edi_pdf_file_id
            + tax_invoices.l10n_th_edi_xml_file_id
            + tax_invoices.l10n_th_edi_pdf_file_id
        )

    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)
        for invoice, invoice_data in invoices_data.items():
            if 'th_inet_send' not in invoice_data['extra_edis']:
                continue
            errors = []
            # A credit or debit note is an e-Tax document by itself, an invoice through its tax invoices.
            for document in (invoice, *invoice.l10n_th_tax_invoice_ids):
                if document.l10n_th_edi_state != 'ready_to_send':
                    continue
                try:
                    document.action_l10n_th_edi_send()
                except UserError as error:
                    errors.append(str(error))
                    continue
                if document.l10n_th_edi_state in ('error', 'unknown'):
                    errors.append(document.l10n_th_edi_error)
            if errors:
                invoice_data['error'] = {'error_title': self.env._("Error when sending to INET"), 'errors': errors}
