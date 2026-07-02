# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools import BinaryBytes


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    def _get_all_extra_edis(self) -> dict:
        # EXTENDS 'account'
        return {
            **super()._get_all_extra_edis(),
            'it_edi_send': {
                'label': _("Send to Tax Agency"),
                'is_applicable': lambda move: move._l10n_it_edi_ready_for_xml_export(),
                'help': _("Send the e-invoice XML to the Italian Tax Agency.")
            }
        }

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------
    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if it_moves := moves.filtered(lambda m: 'it_edi_send' in moves_data[m]['extra_edis']):
            alerts.update(**it_moves._l10n_it_edi_export_data_check())
        return alerts

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------
    def _get_invoice_extra_attachments(self, invoice):
        # EXTENDS 'account'
        return super()._get_invoice_extra_attachments(invoice) + self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_field', '=', 'l10n_it_edi_attachment_file'),
            ('res_id', 'in', invoice.ids),
        ])

    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        if 'it_edi_send' in invoice_data['extra_edis']:
            alerts = invoice._l10n_it_edi_export_data_check()
            if errors := {k: v for k, v in alerts.items() if v.get('level') == 'error'}:
                invoice_data['error'] = {
                    'error_title': _("Errors occurred while creating the e-invoice file:"),
                    'errors': [error['message'] for error in errors.values()],
                }

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        moves = self.env['account.move']
        moves_data = {
            move: move_data
            for move, move_data in invoices_data.items()
            if 'it_edi_send' in move_data['extra_edis']
        }

        # Prepare attachment data
        attachments_vals = {}
        for move, move_data in moves_data.items():
            if errors := {
                k: v
                for k, v in move._l10n_it_edi_export_data_check().items()
                # When actually sending (not alerting), warnings become blocking
                if v.get('level') in ('warning', 'error')
            }:
                move_data['error'] = {
                    'error_title': _("Errors occurred while sending to the SDI:"),
                    'errors': [error['message'] for error in errors.values()],
                }
            elif attachment := move.l10n_it_edi_attachment_file:
                attachments_vals[move] = {'name': move.l10n_it_edi_attachment_name, 'raw': attachment.content}
                moves |= move
            elif pdf_values := move_data.get('pdf_attachment_values'):
                attachments_vals[move] = move._l10n_it_edi_get_attachment_values(pdf_values=pdf_values)
                moves |= move

        # Send
        results = moves._l10n_it_edi_send(attachments_vals)

        # Eventually update attachments with signed data
        correct_moves_data = {k: v for k, v in moves_data.items() if not v.get('error')}
        for move, move_data in correct_moves_data.items():
            if move.l10n_it_edi_attachment_file:
                attachment_name = move.l10n_it_edi_attachment_name
            elif attachment := attachments_vals.get(move):
                attachment_name = attachment['name']
            attachment_data = results.get(attachment_name, {})
            if attachment_data.get('signed') and (signed_data := attachment_data.get('signed_data')):
                move.l10n_it_edi_attachment_file = BinaryBytes(signed_data.encode())
                # Show that those moves couldn't be sent
            if 'error_message' in attachment_data:
                moves_data[move]['error'] = {'error_title': attachment_data['error_message']}

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        move_ids_to_names = {}
        for move, data in invoices_data.items():
            if values := data.get('l10n_it_edi_values'):
                move.l10n_it_edi_attachment_file = BinaryBytes(values['raw'])
                move.l10n_it_edi_attachment_name = values['name']
                move.invalidate_recordset(fnames=['l10n_it_edi_attachment_name', 'l10n_it_edi_attachment_file'])
                move_ids_to_names[move.id] = values['name']

        if move_ids_to_names:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_field', '=', 'l10n_it_edi_attachment_file'),
                ('res_id', 'in', list(move_ids_to_names)),
            ])
            for attachment in attachments:
                attachment.name = move_ids_to_names.get(attachment.res_id)
