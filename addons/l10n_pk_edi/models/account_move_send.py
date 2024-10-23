# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_pk_edi_applicable(self, move):
        return all([
            move._l10n_pk_edi_get_default_enable()
            and move.l10n_pk_edi_state != 'rejected'
        ])

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({
            'pk_edi_send': {
                'label': _("Send to Tax Agency"),
                'is_applicable': self._is_pk_edi_applicable,
                'help': _("Send the e-invoice to the Pakistan FBR(Federal Board of Revenue)."),
            }
        })
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if pk_moves := moves.filtered(
            lambda m: 'pk_edi_send' in moves_data[m]['extra_edis']
            or moves_data[m]['invoice_edi_format'] == 'pk_edi_json'
        ):
            if pk_alerts := pk_moves._l10n_pk_validate_move_lines():
                alerts.update(**pk_alerts)
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    def _get_invoice_extra_attachments(self, invoice):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(invoice) + invoice.l10n_pk_edi_attachment_id

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if (('pk_edi_send' in invoice_data['extra_edis']
                and not invoice.l10n_pk_edi_attachment_id
            ) or (invoice_data['invoice_edi_format'] == 'pk_edi_json'
                and invoice._l10n_pk_edi_get_default_enable()
            )) and (errors := invoice._l10n_pk_validate_move_lines()
        ):
            invoice_data['error'] = {
                'error_title': _("Errors occurred while creating the e-invoice file:"),
                'errors': errors,
            }

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
        if (invoice_data.get('pdf_attachment_values')
            and (('pk_edi_send' in invoice_data['extra_edis']
                    and not invoice.l10n_pk_edi_attachment_id
                ) or (invoice_data['invoice_edi_format'] == 'pk_edi_json'
                    and invoice._l10n_pk_edi_get_default_enable()
                )
            )
        ):
            invoice_data['l10n_pk_edi_values'] = invoice._l10n_pk_edi_get_attachment_values()

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)
        attachments_vals = {}
        moves = self.env['account.move']
        for move, move_data in invoices_data.items():
            if 'pk_edi_send' in move_data['extra_edis']:
                moves |= move
                if attachment := move.l10n_pk_edi_attachment_id:
                    attachments_vals[move] = {
                        'name': attachment.name,
                        'raw': attachment.raw
                    }
                else:
                    attachments_vals[move] = invoices_data[move]['l10n_pk_edi_values']
        if moves:
            moves._l10n_pk_edi_send(attachments_vals)

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)
        attachments_vals = [
            invoice_data.get('l10n_pk_edi_values')
            for invoice_data in invoices_data.values()
            if invoice_data.get('l10n_pk_edi_values')
        ]
        if attachments_vals:
            attachments = self.env['ir.attachment'].sudo().create(attachments_vals)
            res_ids = [attachment.res_id for attachment in attachments]
            self.env['account.move'].browse(res_ids).invalidate_recordset(
                fnames=[
                    'l10n_pk_edi_attachment_id',
                    'l10n_pk_edi_attachment_file'
                ]
            )
