import uuid
from markupsafe import Markup
from urllib.parse import quote, urlencode, urlparse

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move']

    l10n_tr_nilvera_uuid = fields.Char(
        string="Nilvera Document UUID",
        copy=False,
        readonly=True,
        default=lambda self: str(uuid.uuid4()),
        help="Universally unique identifier of the Invoice",
    )
    l10n_tr_nilvera_send_status = fields.Selection(
        selection=[
            ('error', "Error (check chatter)"),
            ('not_sent', "Not sent"),
            ('sent', "Sent and waiting response"),
            ('succeed', "Successful"),
            ('waiting', "Waiting"),
            ('unknown', "Unknown"),
        ],
        string="Nilvera Status",
        readonly=True,
        copy=False,
        default='not_sent',
    )

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'TR1.2' in customization_id.text:
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def button_draft(self):
        # EXTENDS account
        for move in self:
            if move.l10n_tr_nilvera_uuid and move.l10n_tr_nilvera_send_status != 'not_sent':
                raise UserError(_("You cannot reset to draft an entry that has been sent to Nilvera."))
        super().button_draft()

    def _l10n_tr_nilvera_submit_einvoice(self, xml_file, customer_alias):
        self._l10n_tr_nilvera_submit_document(
            xml_file=xml_file,
            endpoint=f"/einvoice/Send/Xml?{urlencode({'Alias': customer_alias})}",
        )

    def _l10n_tr_nilvera_submit_earchive(self, xml_file):
        self._l10n_tr_nilvera_submit_document(
            xml_file=xml_file,
            endpoint="/earchive/Send/Xml",
        )

    def _l10n_tr_nilvera_submit_document(self, xml_file, endpoint, post_series=True):
        """
        Submits an e-invoice or e-archive document to Nilvera for processing.

        :param xml_file: The XML file to be submitted.
        :type xml_file: file-like object
        :param endpoint: The Nilvera API endpoint for submission.
        :type endpoint: str
        :param post_series: Whether to attempt posting the series/sequence to Nilvera if it is missing.
                            Defaults to True. Useful for avoiding an infinite loop.
        :type post_series: bool
        :raises UserError: If the API key lacks necessary rights (401 or 403 responses), if the response
                            indicates a client error (4xx), or if a server error occurs (500).
        :return: None
        """
        with _get_nilvera_client(self.env.company) as client:
            response = client.request(
                "POST",
                endpoint,
                files={'file': (xml_file.name, xml_file, 'application/xml')},
                handle_response=False,
            )

            if response.status_code == 200:
                self.l10n_tr_nilvera_send_status = 'sent'
            elif response.status_code in {401, 403}:
                raise UserError(_("Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."))
            elif 400 <= response.status_code < 500:
                error_message, error_codes = self._l10n_tr_nilvera_einvoice_get_error_messages_from_response(response)

                # If the sequence/series is not found on Nilvera, add it then retry.
                if 3009 in error_codes and post_series:
                    self._l10n_tr_nilvera_post_series(endpoint, client)
                    return self._l10n_tr_nilvera_submit_document(xml_file, endpoint, post_series=False)
                raise UserError(error_message)
            elif response.status_code == 500:
                return UserError(_("Server error from Nilvera, please try again later."))

            self.message_post(body=_("The invoice has been successfully sent to Nilvera."))

    def _l10n_tr_nilvera_post_series(self, endpoint, client):
        """Post the series to Nilvera based on the endpoint."""
        path = urlparse(endpoint).path  # Remove query params from te endpoint.
        if path == "/einvoice/Send/Xml":
            series_endpoint = "/einvoice/Series"
        elif path == "/earchive/Send/Xml":
            series_endpoint = "/earchive/Series"
        else:
            # Return early if endpoint couldn't be matched.
            return

        if not self.sequence_prefix:
            return

        series = self.sequence_prefix.split('/', 1)[0]
        client.request(
            "POST",
            series_endpoint,
            json={
                'Name': series,
                'IsActive': True,
                'IsDefault': False,
            },
        )

    def _l10n_tr_nilvera_get_submitted_document_status(self):
        with _get_nilvera_client(self.env.company) as client:
            for invoice in self:
                response = client.request(
                    "GET",
                    f"/einvoice/sale/{invoice.l10n_tr_nilvera_uuid}/Status",
                )

                nilvera_status = response.get('InvoiceStatus', {}).get('Code')
                if nilvera_status in dict(invoice._fields['l10n_tr_nilvera_send_status'].selection):
                    invoice.l10n_tr_nilvera_send_status = nilvera_status
                    if nilvera_status == 'error':
                        invoice.message_post(
                            body=Markup(
                                "%s<br/>%s - %s<br/>"
                            ) % (
                                _("The invoice couldn't be sent to the recipient."),
                                response['InvoiceStatus'].get('Description'),
                                response['InvoiceStatus'].get('DetailDescription'),
                            )
                        )
                else:
                    invoice.message_post(body=_("The invoice status couldn't be retrieved from Nilvera."))

    def _l10n_tr_nilvera_get_documents(self):
        with _get_nilvera_client(self.env.company) as client:
            response = client.request(
                "GET",
                "/einvoice/Purchase",
            )

            if not response.get('Content'):
                return

            journal = self.env.company.l10n_tr_nilvera_purchase_journal_id
            if not journal:
                journal = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(self.env.company),
                    ('type', '=', 'purchase'),
                ], limit=1)

            document_uuids = [content.get('UUID') for content in response.get('Content')]
            document_uuids_count = dict(self.env['account.move']._read_group(
                [('l10n_tr_nilvera_uuid', 'in', document_uuids)],
                groupby=['l10n_tr_nilvera_uuid'],
                aggregates=['__count'],
            ))
            for document_uuid in document_uuids:
                # Skip invoices that have already been downloaded.
                if document_uuid in document_uuids_count:
                    continue
                move = self._l10n_tr_nilvera_get_invoice_from_uuid(client, journal, document_uuid)
                self._l10n_tr_nilvera_add_pdf_to_invoice(client, move, document_uuid)
                self._cr.commit()

    def _l10n_tr_nilvera_get_invoice_from_uuid(self, client, journal, document_uuid):
        response = client.request(
            "GET",
            f"/einvoice/Purchase/{quote(document_uuid)}/xml",
        )

        attachment_vals = {
            'name': 'attachment.xml',
            'raw': response,
            'type': 'binary',
            'mimetype': 'application/xml',
        }

        attachment = self.env['ir.attachment'].create(attachment_vals)
        try:
            move = journal.with_context(
                default_move_type='in_invoice',
                default_l10n_tr_nilvera_uuid=document_uuid,
            )._create_document_from_attachment(attachment.id)

            # If move creation was successful, update the attachment name with the bill reference.
            if move.ref:
                attachment.name = f'{move.ref}.xml'

            move._message_log(body=_("Nilvera document has been received successfully"))
        except Exception:   # noqa: BLE001
            # If the invoice creation fails, create an empty invoice with the attachment. The PDF will be
            # added in a later step as well.
            move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'company_id': self.env.company.id,
                'l10n_tr_nilvera_uuid': document_uuid,
            })
            attachment.write({
                'res_model': 'account.move',
                'res_id': move.id,
            })

        return move

    def _l10n_tr_nilvera_add_pdf_to_invoice(self, client, invoice, document_uuid):
        response = client.request(
            "GET",
            f"/einvoice/Purchase/{quote(document_uuid)}/pdf",
        )

        filename = f'{invoice.ref}.pdf' if invoice.ref else 'Nilvera PDF.pdf'

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'res_id': invoice.id,
            'res_model': 'account.move',
            'datas': response,
            'type': 'binary',
            'mimetype': 'application/pdf',
        })

        if (invoice.message_main_attachment_id
                and invoice.message_main_attachment_id.name.endswith('.xml')
                and 'pdf' not in invoice.message_main_attachment_id.mimetype):
            invoice.message_main_attachment_id = attachment
        invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachment.ids)

    def _l10n_tr_nilvera_einvoice_get_error_messages_from_response(self, response):
        msg = ""
        error_codes = []

        response_json = response.json()
        if errors := response_json.get('Errors'):
            msg += _("The invoice couldn't be sent due to the following errors:\n")
            for error in errors:
                msg += "%s - %s: %s\n" % (error.get('Code'), error.get('Description'), error.get('Detail'))
                error_codes.append(error.get('Code'))

        return msg, error_codes

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_nilvera_get_new_documents(self):
        self._l10n_tr_nilvera_get_documents()

    def _cron_nilvera_get_invoice_status(self):
        invoices_to_update = self.env['account.move'].search([
            ('l10n_tr_nilvera_send_status', 'in', ['waiting', 'sent']),
        ])
        invoices_to_update._l10n_tr_nilvera_get_submitted_document_status()
