# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import time
from collections import defaultdict

from odoo import SUPERUSER_ID, _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    l10n_my_edi_enable = fields.Boolean(
        compute='_compute_l10n_my_edi_enable',
    )
    l10n_my_edi_send_checkbox = fields.Boolean(
        compute='_compute_l10n_my_edi_send_checkbox',
        string='Send to MyInvois',
        readonly=False,
        store=True,
    )

    def _get_wizard_values(self):
        # EXTENDS 'account'
        values = super()._get_wizard_values()
        values['l10n_my_edi_send'] = self.l10n_my_edi_send_checkbox
        return values

    @api.depends('move_ids')
    def _compute_l10n_my_edi_enable(self):
        """
        E-invoicing is a legal requirement that doesn't require any special action from the user,
        so we enable by default.
        """
        # If there is no proxy user set and active, the feature shouldn't be available on invoices.
        for wizard in self:
            wizard.l10n_my_edi_enable = any(self._l10n_my_edi_need_edi(move) for move in wizard.move_ids)

    @api.depends('l10n_my_edi_enable')
    def _compute_l10n_my_edi_send_checkbox(self):
        for wizard in self:
            wizard.l10n_my_edi_send_checkbox = wizard.l10n_my_edi_enable

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

    @api.depends('l10n_my_edi_send_checkbox')
    def _compute_mail_attachments_widget(self):
        # EXTENDS 'account' - add depends
        super()._compute_mail_attachments_widget()

    @api.model
    def _hook_invoice_document_before_pdf_report_render(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._hook_invoice_document_before_pdf_report_render(invoice, invoice_data)
        self._l10n_my_edi_generate_myinvois_xml(invoice, invoice_data)

    @api.model
    def _l10n_my_edi_generate_myinvois_xml(self, invoice, invoice_data):
        # It should always be generated when sending.
        if invoice_data.get('l10n_my_edi_send') or invoice_data.get('l10n_my_edi_generate'):
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
    def _l10n_my_edi_need_edi(self, invoice, acceptable_states=None):
        """ This will determine if a specific invoice is fit to interact with the API from here.
        When submitting, we want to avoid any invoice that already have a state (which means they were submitted) but
        when fetching the updated states, in_progress invoices are acceptable.
        """
        return (invoice.is_invoice()
                and invoice.state == 'posted'
                and invoice.country_code == 'MY'
                and (not invoice.l10n_my_edi_state or acceptable_states and invoice.l10n_my_edi_state in acceptable_states)
                and invoice.company_id.l10n_my_edi_proxy_user_id)

    @api.model
    def _call_web_service_before_invoice_pdf_render(self, invoices_data):
        # EXTENDS 'account'
        super()._call_web_service_before_invoice_pdf_render(invoices_data)

        xml_contents = defaultdict(list)
        moves = self.env['account.move']
        # This step is skipped if the move was sent, but not validated.
        for move, move_data in invoices_data.items():
            if not move_data.get('l10n_my_edi_send') or not self._l10n_my_edi_need_edi(move):
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

        moves = self.env['account.move']
        for move, move_data in invoices_data.items():
            if not move_data.get('l10n_my_edi_send') or not self._l10n_my_edi_need_edi(move, acceptable_states={'in_progress'}):
                continue

            moves |= move

        if moves:
            # This update can fail, but we don't consider that as a blocking error.
            # If the api request fails (timeout, validation not finished, ...) it'll be retried in the cron `cron_name`.
            invoices = self.env['account.move'].concat(*list(invoices_data.keys()))

            retry = 0
            errors, any_in_progress = invoices._l10n_my_edi_fetch_updated_statuses()
            while any_in_progress and retry < 2:
                time.sleep(1)  # We wait a second before retrying.
                errors, any_in_progress = invoices._l10n_my_edi_fetch_updated_statuses()
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
    def _link_invoice_documents(self, invoice, invoice_data):
        # EXTENDS 'account'
        super()._link_invoice_documents(invoice, invoice_data)

        attachment_vals = invoice_data.get('myinvois_attachments')
        if attachment_vals:
            self.env['ir.attachment'].with_user(SUPERUSER_ID).create(attachment_vals)
            invoice.invalidate_recordset(fnames=['l10n_my_edi_file_id', 'l10n_my_edi_file'])
