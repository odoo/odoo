import uuid
from markupsafe import Markup
from urllib.parse import quote, urlencode, urlparse

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client

MOVE_TYPE_CATEGORY_MAP = {
    "out_invoice": {
        "earchive": "invoices",
        "einvoice": "sale",
    },
    "in_invoice": {
        "einvoice": "purchase",
    },
}

CATEGORY_MOVE_TYPE_MAP = {
    "invoices": "out_invoice",
    "sale": "out_invoice",
    "purchase": "in_invoice",
}


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
            ('error', "Error"),
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

    def _get_import_file_type(self, file_data):
        """ Identify Nilvera UBL files. """
        # EXTENDS 'account'
        if (
            file_data['xml_tree'] is not None
            and (customization_id := file_data['xml_tree'].findtext('{*}CustomizationID'))
            and 'TR1.2' in customization_id
        ):
            return 'account.edi.xml.ubl.tr'

        return super()._get_import_file_type(file_data)

    def _l10n_tr_types_to_update_status(self):
        return list(MOVE_TYPE_CATEGORY_MAP)

    def _l10n_tr_get_document_category(self, invoice_channel):
        return MOVE_TYPE_CATEGORY_MAP.get(self.move_type, {}).get(invoice_channel)

    def _l10n_tr_get_category_move_type(self, document_category):
        return CATEGORY_MOVE_TYPE_MAP.get(document_category.lower())

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'TR1.2' in customization_id.text:
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def button_draft(self):
        # EXTENDS account
        for move in self:
            if (
                not move.company_id.l10n_tr_nilvera_use_test_env
                and move.l10n_tr_nilvera_uuid
                and move.l10n_tr_nilvera_send_status != 'not_sent'
            ):
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
                self.is_move_sent = True
                self.l10n_tr_nilvera_send_status = 'sent'
            elif response.status_code in {401, 403}:
                raise UserError(_("Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."))
            elif 400 <= response.status_code < 500:
                error_message, error_codes = self._l10n_tr_nilvera_einvoice_get_error_messages_from_response(response)

                # If the sequence/series is not found on Nilvera, add it then retry.
                if 3009 in error_codes and post_series:
                    self._l10n_tr_nilvera_post_series(endpoint, client)
                    xml_file.seek(0)    # reset stream before retry, as previous POST moved the buffer to the EOF
                    return self._l10n_tr_nilvera_submit_document(xml_file, endpoint, post_series=False)
                raise UserError(error_message)
            elif response.status_code == 500:
                raise UserError(_("Server error from Nilvera, please try again later."))

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
                invoice_channel = invoice.partner_id.l10n_tr_nilvera_customer_status
                document_category = invoice._l10n_tr_get_document_category(invoice_channel)
                if not document_category or not invoice_channel:
                    continue

                response = client.request(
                    "GET",
                    f"/{invoice_channel}/{quote(document_category)}/{invoice.l10n_tr_nilvera_uuid}/Status",
                )

                nilvera_status = response.get('InvoiceStatus', {}).get('Code') or response.get('StatusCode')
                if nilvera_status in dict(invoice._fields['l10n_tr_nilvera_send_status'].selection):
                    invoice.l10n_tr_nilvera_send_status = nilvera_status
                    if nilvera_status == 'error':
                        invoice.message_post(
                            body=Markup(
                                "%s<br/>%s - %s<br/>"
                            ) % (
                                _("The invoice couldn't be sent to the recipient."),
                                response.get('InvoiceStatus', {}).get('Description') or response.get('StatusDetail'),
                                response.get('InvoiceStatus', {}).get('DetailDescription') or response.get('ReportStatus'),
                            )
                        )
                else:
                    invoice.message_post(body=_("The invoice status couldn't be retrieved from Nilvera."))

    def _l10n_tr_nilvera_get_documents(self, invoice_channel="einvoice", document_category="Purchase", journal_type="in_invoice"):
        with _get_nilvera_client(self.env.company) as client:
            response = client.request("GET", f"/{invoice_channel}/{quote(document_category)}", params={"StatusCode": ["succeed"]})
            if not response.get('Content'):
                return
            journal = self._l10n_tr_get_nilvera_invoice_journal(journal_type)
            document_uuids, document_uuids_records, document_uuids_references = self._l10n_tr_build_document_uuids_list(response)
            moves = self.env['account.move']
            for document_uuid in document_uuids:
                # Skip invoices that have already been downloaded.
                if document_uuid in document_uuids_records:
                    continue
                move = document_uuids_records.get(document_uuid)
                # If an account.move doesn't exist, create it and attach the document
                if not move:
                    move = self._l10n_tr_nilvera_get_invoice_from_uuid(client, journal, document_uuid, document_category, invoice_channel)
                    self._l10n_tr_nilvera_add_pdf_to_invoice(client, move, document_uuid, document_category, invoice_channel)
                # If account.move exists, but doesn't have a reference and its reference is found in the nilvera document references, attach the document
                elif not move.ref and (nilvera_reference := document_uuids_references.get(document_uuid)):
                    move.ref = nilvera_reference
                    self._l10n_tr_nilvera_add_pdf_to_invoice(client, move, document_uuid, document_category, invoice_channel)
                moves |= move
                self.env.cr.commit()
            journal._notify_einvoices_received(moves)

    def _l10n_tr_get_nilvera_invoice_journal(self, journal_type):
        journal = self._l10n_tr_get_document_category_default_journal(journal_type)
        if not journal:
            journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
                ('type', '=', f'{journal_type}'),
            ], limit=1)
        return journal

    def _l10n_tr_get_document_category_default_journal(self, journal_type):
        if journal_type == "purchase":
            return self.env.company.l10n_tr_nilvera_purchase_journal_id
        return None

    def _l10n_tr_build_document_uuids_list(self, response):
        contents = response.get("Content", [])
        document_uuids = [content.get("UUID") for content in contents if content.get("UUID")]
        # Should be unique per invoice so we get the records with the invoice to use the records
        document_uuids_records = dict(self.env["account.move"]._read_group([("l10n_tr_nilvera_uuid", "in", document_uuids)], groupby=["l10n_tr_nilvera_uuid", "id"]))
        document_uuids_references = {
            content["UUID"]: content["InvoiceNumber"]
            for content in contents
            if content.get("UUID") and content.get("InvoiceNumber")
        }

        return document_uuids, document_uuids_records, document_uuids_references

    def _l10n_tr_nilvera_get_invoice_from_uuid(self, client, journal, document_uuid, document_category="Purchase", invoice_channel="einvoice"):
        response = client.request(
            "GET",
            f"/{invoice_channel}/{quote(document_category)}/{quote(document_uuid)}/xml",
            params={"StatusCode": ["succeed"]},
        )

        attachment_vals = {
            'name': 'attachment.xml',
            'raw': response,
            'type': 'binary',
            'mimetype': 'application/xml',
        }

        attachment = self.env['ir.attachment'].create(attachment_vals)
        move_type = self._l10n_tr_get_category_move_type(document_category)
        try:
            move = journal.with_context(
                default_move_type=move_type,
                default_l10n_tr_nilvera_uuid=document_uuid,
                default_message_main_attachment_id=attachment.id,
                default_l10n_tr_nilvera_send_status='succeed',
            )._create_document_from_attachment(attachment.id)

            # If move creation was successful, update the attachment name with the bill reference.
            if move.ref:
                attachment.name = f'{move.ref}.xml'

            move._message_log(body=_("Nilvera document has been received successfully"))
        except Exception:   # noqa: BLE001
            # If the invoice creation fails, create an empty invoice with the attachment. The PDF will be
            # added in a later step as well. Nilvera only returns uuid of the successful attachments.
            move = self.env['account.move'].create({
                'move_type': move_type,
                'company_id': self.env.company.id,
                'l10n_tr_nilvera_uuid': document_uuid,
                'l10n_tr_nilvera_send_status': 'succeed',
                'message_main_attachment_id': attachment.id,
            })
            attachment.write({
                'res_model': 'account.move',
                'res_id': move.id,
            })

        return move

    def _l10n_tr_nilvera_add_pdf_to_invoice(self, client, invoice, document_uuid, document_category="Purchase", invoice_channel="einvoice"):
        response = client.request(
            "GET",
            f"/{invoice_channel}/{quote(document_category)}/{quote(document_uuid)}/pdf",
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
        # The created attachement coming form Nilvera should be the main attachment
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

    def _l10n_tr_nilvera_einvoice_check_invalid_subscription_dates(self):
        if 'deferred_start_date' not in self.invoice_line_ids._fields:
            return False

        # Ensure that either no lines have the start and end dates or all lines have the same start and end dates.
        lines_to_check = self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
        if not (subscription_lines := lines_to_check.filtered('deferred_start_date')):
            return False

        return len(subscription_lines) != len(lines_to_check) or len(set(subscription_lines.mapped(
            lambda aml: (aml.deferred_start_date, aml.deferred_end_date))
        )) > 1

    def _l10n_tr_nilvera_einvoice_check_negative_lines(self):
        return any(
            line.display_type not in {'line_note', 'line_section'}
            and (line.quantity < 0 or line.price_unit < 0)
            for line in self.invoice_line_ids
        )

    def _get_partner_l10n_tr_nilvera_customer_alias_name(self):
        # Allows overriding the default customer alias with a custom one.
        self.ensure_one()
        return self.partner_id.l10n_tr_nilvera_customer_alias_id.name

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _l10n_tr_nilvera_company_get_documents(self, invoice_channel, category, journal_type):
        for company in self.env.companies:
            if company.country_code != "TR" or not company.l10n_tr_nilvera_api_key:
                continue
            self.with_company(company)._l10n_tr_nilvera_get_documents(invoice_channel, category, journal_type)

    def _cron_nilvera_get_new_einvoice_purchase_documents(self):
        self._l10n_tr_nilvera_company_get_documents("einvoice", "Purchase", "purchase")

    def _cron_nilvera_get_new_einvoice_sale_documents(self):
        self._l10n_tr_nilvera_company_get_documents("einvoice", "Sale", "sale")

    def _cron_nilvera_get_new_earchive_sale_documents(self):
        self._l10n_tr_nilvera_company_get_documents("earchive", "Invoices", "sale")

    def _cron_nilvera_get_invoice_status(self):
        invoices_to_update = self.env['account.move'].search([
            ('l10n_tr_nilvera_send_status', 'in', ['waiting', 'sent']),
            ('move_type', 'in', self._l10n_tr_types_to_update_status()),
        ])
        invoices_to_update._l10n_tr_nilvera_get_submitted_document_status()
