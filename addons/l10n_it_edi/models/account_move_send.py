# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_it_edi_applicable(self, move):
        return all([
            move.company_id.account_fiscal_country_id.code == 'IT'
            and move._l10n_it_edi_ready_for_xml_export()
            and move.l10n_it_edi_state != 'rejected'
        ])

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'it_edi_send': {'label': _("Send to Tax Agency"), 'is_applicable': self._is_it_edi_applicable, 'help': _("Send the e-invoice XML to the Italian Tax Agency.")}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if it_moves := moves.filtered(lambda m: 'it_edi_send' in moves_data[m]['extra_edis'] or moves_data[m]['invoice_edi_format'] == 'it_edi_xml'):
            if it_alerts := it_moves._l10n_it_edi_export_data_check():
                alerts.update(**it_alerts)
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, invoice):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(invoice) + invoice.l10n_it_edi_attachment_id

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if (
                ('it_edi_send' in invoice_data['extra_edis'] and not invoice.l10n_it_edi_attachment_id)
                or (invoice_data['invoice_edi_format'] == 'it_edi_xml' and invoice._l10n_it_edi_ready_for_xml_export())
        ):
            if errors := invoice._l10n_it_edi_export_data_check():
                invoice_data['error'] = {
                    'error_title': _("Errors occurred while creating the e-invoice file:"),
                    'errors': errors,
                }

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
        if (
            invoice_data.get('pdf_attachment_values')
            and (
                ('it_edi_send' in invoice_data['extra_edis'] and not invoice.l10n_it_edi_attachment_id)
                or (invoice_data['invoice_edi_format'] == 'it_edi_xml' and invoice._l10n_it_edi_ready_for_xml_export())
            )
        ):
            invoice_data['l10n_it_edi_values'] = invoice._l10n_it_edi_get_attachment_values(
                pdf_values=invoice_data['pdf_attachment_values'])

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        attachments_vals = {}
        moves = self.env['account.move']
        for move, move_data in invoices_data.items():
            if 'it_edi_send' in move_data['extra_edis']:
                moves |= move
                if attachment := move.l10n_it_edi_attachment_id:
                    attachments_vals[move] = {'name': attachment.name, 'raw': attachment.raw}
                else:
                    attachments_vals[move] = invoices_data[move]['l10n_it_edi_values']
        moves._l10n_it_edi_send(attachments_vals)

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        attachments_vals = [
            invoice_data.get('l10n_it_edi_values')
            for invoice_data in invoices_data.values()
            if invoice_data.get('l10n_it_edi_values')
        ]
        if attachments_vals:
            attachments = self.env['ir.attachment'].sudo().create(attachments_vals)
            res_ids = attachments.mapped('res_id')
            self.env['account.move'].browse(res_ids).invalidate_recordset(fnames=['l10n_it_edi_attachment_id', 'l10n_it_edi_attachment_file'])
