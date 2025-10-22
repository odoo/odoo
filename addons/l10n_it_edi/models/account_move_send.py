# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, models
import base64


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

            # Invite the user to authorize Odoo and start using IT EDI in production mode
            if 'prod' not in it_moves.mapped('l10n_it_edi_proxy_mode'):
                alerts['l10n_it_edi_invite_authorize'] = {
                    'level': 'info',
                    'message': _("You must authorize Odoo in the Settings to use the IT EDI in production mode."),
                    'action_text': _("View Settings"),
                    'action': {
                        'name': _("Settings"),
                        'type': 'ir.actions.act_url',
                        'target': 'self',
                        'url': '/odoo/settings#l10n_it_edi_setting',
                    },
                }

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
        if (
                ('it_edi_send' in invoice_data['extra_edis'] and not invoice.l10n_it_edi_attachment_file)
                or (invoice_data['invoice_edi_format'] == 'it_edi_xml' and invoice._l10n_it_edi_ready_for_xml_export())
        ):
            if errors := invoice._l10n_it_edi_export_data_check():
                invoice_data['error'] = {
                    'error_title': _("Errors occurred while creating the e-invoice file:"),
                    'errors': [error['message'] for error in errors.values()],
                }

    def _hook_invoice_document_after_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_after_pdf_report_render(invoice, invoice_data)
        if (
            invoice_data.get('pdf_attachment_values')
            and (
                ('it_edi_send' in invoice_data['extra_edis'] and not invoice.l10n_it_edi_attachment_file)
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

        # Filter only l10n_it_edi attachments
        moves_data = {
            move: move_data
            for move, move_data in invoices_data.items()
            if 'it_edi_send' in move_data['extra_edis']
        }

        # Prepare attachment data
        for move, move_data in moves_data.items():
            if attachment := move.l10n_it_edi_attachment_file:
                attachments_vals[move] = {'name': move.l10n_it_edi_attachment_name, 'raw': attachment}
                moves |= move
            elif edi_values := move_data.get('l10n_it_edi_values'):
                attachments_vals[move] = edi_values
                moves |= move

        # Send
        results = moves._l10n_it_edi_send(attachments_vals)

        # Eventually update attachments with signed data
        for move, move_data in moves_data.items():
            if move.l10n_it_edi_attachment_file:
                attachment_name = move.l10n_it_edi_attachment_name
            elif attachment := move_data.get('l10n_it_edi_values'):
                attachment_name = attachment['name']
            attachment_data = results.get(attachment_name, {})
            if attachment_data.get('signed') and (signed_data := attachment_data.get('signed_data')):
                attachment['raw'] = signed_data.encode()
                # Show that those moves couldn't be sent
            if 'error_message' in attachment_data:
                moves_data[move]['error'] = attachment_data['error_message']

    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        move_ids_to_names = {}
        for move, data in invoices_data.items():
            if values := data.get('l10n_it_edi_values'):
                move.l10n_it_edi_attachment_file = base64.b64encode(values['raw'])
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
