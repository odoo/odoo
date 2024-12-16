# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import time
from collections import defaultdict

from odoo import _, api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    @api.model
    def _is_my_edi_applicable(self, move):
        return (move.is_invoice()
                and move.state == 'posted'
                and move.country_code == 'MY'
                and not move.l10n_my_edi_state
                and move.company_id.l10n_my_edi_proxy_user_id)

    def _get_all_extra_edis(self):
        # EXTENDS 'account'
        res = super()._get_all_extra_edis()
        res.update({'my_myinvois_send': {'label': _("Send to MyInvois"), 'is_applicable': self._is_my_edi_applicable}})
        return res

    # -------------------------------------------------------------------------
    # ALERTS
    # -------------------------------------------------------------------------

    def _get_alerts(self, moves, moves_data):
        # EXTENDS 'account'
        alerts = super()._get_alerts(moves, moves_data)
        if waiting_moves := moves.filtered(lambda m: m.l10n_my_edi_state == 'in_progress'):
            alerts['l10n_my_edi_warning_waiting_moves'] = {
                'message': _(
                    "The following invoice(s) are waiting for validation from MyInvois: %(move_name_list)s."
                    "Their status will be updated later on, or you can do it manually from the form view.",
                    move_name_list=', '.join(waiting_moves.mapped('name'))
                ),
                'action_text': _("View Invoice(s)"),
                'action': waiting_moves._get_records_action(name=_("Check Invoice(s)")),
            }
        return alerts

    # -------------------------------------------------------------------------
    # ATTACHMENTS
    # -------------------------------------------------------------------------

    @api.model
    def _get_invoice_extra_attachments(self, move):
        """ We are required to either:
            - Attach a QR code to the invoice PDF, that points to the e-invoice on the MyInvois platform
            - Attach the XML file we generated
        We will use to later for simplicity. It is unclear if the shared xml should be digitally signed or not.
        """
        # EXTENDS 'account'
        return (
            super()._get_invoice_extra_attachments(move)
            + move.l10n_my_edi_file_id
        )

    # -------------------------------------------------------------------------
    # SENDING METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _l10n_my_edi_generate_myinvois_xml(self, invoice, invoice_data):
        need_file = (
            (invoice_data['invoice_edi_format'] == 'my_myinvois' and invoice.company_id.l10n_my_edi_proxy_user_id)
            or 'my_myinvois_send' in invoice_data['extra_edis']
        )
        # It should always be generated when sending.
        if need_file:
            # We don't pre-check the configuration, the ubl export will handle that part.
            xml_content, errors = invoice._l10n_my_edi_generate_invoice_xml()
            if errors:
                invoice_data['error'] = {
                    'error_title': _('Error when generating MyInvois file:'),
                    'errors': errors,
                }
            else:
                invoice_data['myinvois_attachments'] = [{
                    'name': f'{invoice.name.replace("/", "_")}_myinvois.xml',
                    'raw': xml_content,
                    'mimetype': 'application/xml',
                    'res_model': invoice._name,
                    'res_id': invoice.id,
                    'res_field': 'l10n_my_edi_file',  # Binary field
                }]

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        self._l10n_my_edi_generate_myinvois_xml(invoice, invoice_data)

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        xml_contents = defaultdict(list)
        moves = self.env['account.move']
        # This step is skipped if the move was sent, but not validated.
        for move, move_data in invoices_data.items():
            if 'my_myinvois_send' not in move_data['extra_edis']:
                continue

            moves |= move
            if 'myinvois_attachments' in move_data:
                xml_content = move_data['myinvois_attachments'][0]['raw'].decode('utf-8')
            # If the invoice was downloaded but not sent, the json file could already be there.
            elif move.l10n_my_edi_file:
                xml_content = base64.b64decode(move.l10n_my_edi_file).decode('utf-8')
            # If we don't have the file data and the file, we will regenerate it.
            else:
                self._l10n_my_edi_generate_myinvois_xml(move, move_data)
                if 'myinvois_attachments' not in move_data:
                    continue  # If an error occurred, it'll be in move_data['error'] so we can skip this invoice
                xml_content = move_data['myinvois_attachments'][0]['raw'].decode('utf-8')
            xml_contents[move] = xml_content

        if moves and xml_contents:
            errors = moves._l10n_my_edi_submit_documents(xml_contents)

            if errors:
                for move, move_data in invoices_data.items():
                    if move in errors:
                        move_data['error'] = {
                            'error_title': _('Error when sending the invoices to the E-invoicing service.'),
                            'errors': errors[move],
                        }

            # Whatever happened, we need to commit once at this point, because another api call is done later on
            # And in case of single invoice, a request error could raise => We would lose the uuid etc.
            if self._can_commit():
                self._cr.commit()

    def _call_web_service_after_invoice_pdf_render(self, invoices_data):
        """
        We need to get the submission status (valid, invalid) now for the flow to make sense.
        If we follow their documentation, the status should be available near instantly (in 2s of the submission) which
        means that it should be there in the time we get the submission response back and generate the invoice(s) pdf.

        We will try up to three time with a 2s delay to make it happen. It should cover most of the use cases, as long as
        there are no network issues/...

        If after three time the invoice still has not been processed, we will move on and leave the update to the
        scheduled action that fetches new incoming invoices and update statuses at the same time.
        """
        # EXTENDS 'account'
        super()._call_web_service_after_invoice_pdf_render(invoices_data)

        moves_in_progress = self.env['account.move']
        for move, move_data in invoices_data.items():
            if 'my_myinvois_send' not in move_data['extra_edis'] or move.l10n_my_edi_state != 'in_progress':
                continue

            moves_in_progress |= move

        # We want to ensure that we do not do anything more for moves which failed basic validations.
        if moves_in_progress:
            # This update can fail, but we don't consider that as a blocking error.
            # If the api request fails (timeout, validation not finished, ...) it'll be retried in the cron `ir_cron_myinvois_sync`.
            retry = 0
            errors, any_in_progress = moves_in_progress._l10n_my_edi_fetch_updated_statuses()
            while any_in_progress and retry < 2:
                time.sleep(1)  # We wait a second before retrying.
                errors, any_in_progress = moves_in_progress._l10n_my_edi_fetch_updated_statuses()
                retry += 1

            # While technically an in_progress status is not an error, it won't hurt much to display it as such.
            # The "error" message in this case should be clear enough.
            if errors:
                for move, move_data in invoices_data.items():
                    if move in errors:
                        move_data['error'] = {
                            'error_title': _('Error when fetching statuses from the E-invoicing service.'),
                            'errors': errors[move],
                        }

            # We commit again if possible, to ensure that the invoice status is set in the database in case of errors later.
            if self._can_commit():
                self._cr.commit()

    @api.model
    def _link_invoice_documents(self, invoices_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoices_data)

        attachments_vals = []
        for invoice_data in invoices_data.values():
            attachments_vals.extend(invoice_data.get('myinvois_attachments', []))

        if attachments_vals:
            attachments = self.env['ir.attachment'].sudo().create(invoice_data.get('myinvois_attachments'))
            res_ids = attachments.mapped('res_id')
            self.env['account.move'].browse(res_ids).invalidate_recordset(fnames=['l10n_my_edi_file_id', 'l10n_my_edi_file'])
