import base64
import logging
import uuid
from json import JSONDecodeError
from urllib.parse import quote, urlencode, urlparse

from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_tr_nilvera.lib.nilvera_client import _get_nilvera_client

_logger = logging.getLogger(__name__)

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
    l10n_tr_gib_invoice_scenario = fields.Selection(
        selection=[
            ('TEMELFATURA', "Basic"),
            ('KAMU', "Public Sector"),
            ('TICARIFATURA', "Commercial"),
        ],
        default='TEMELFATURA',
        string="Invoice Scenario",
        help="The scenario of the invoice to be sent to GİB.",
    )
    l10n_tr_gib_invoice_type = fields.Selection(
        compute='_compute_l10n_tr_gib_invoice_type',
        store=True,
        readonly=False,
        default='SATIS',
        string="GIB Invoice Type",
        selection=[
            ('SATIS', "Sales"),
            ('TEVKIFAT', "Withholding"),
            ('IHRACKAYITLI', "Registered for Export"),
            ('ISTISNA', "Tax Exempt"),
            ('IADE', "Return"),
            ('TEVKIFATIADE', "Withholding Return"),
        ],
        help="The type of invoice to be sent to GİB.",
    )
    l10n_tr_is_export_invoice = fields.Boolean(string="GİB Product Export Invoice")
    l10n_tr_shipping_type = fields.Selection(
        selection=[
            ('1', "Sea Transportation"),
            ('2', "Railway Transportation"),
            ('3', "Road Transportation"),
            ('4', "Air Transportation"),
            ('5', "Post"),
            ('6', "Combined Transportation"),
            ('7', "Fixed Transportation"),
            ('8', "Domestic Water Transportation"),
            ('9', "Invalid Transportation Method"),
        ],
        string="Shipping Method",
        help="The type of shipping.",
    )
    l10n_tr_exemption_code_id = fields.Many2one(
        comodel_name='l10n_tr_nilvera_einvoice.account.tax.code',
        compute='_compute_l10n_tr_exemption_code_id',
        store=True,
        readonly=False,
        string="Exemption Reason",
        help="The exception reason of the invoice.",
    )
    l10n_tr_exemption_code_domain_list = fields.Json(compute='_compute_l10n_tr_exemption_code_domain_list')
    l10n_tr_nilvera_customer_status = fields.Selection(
        string="Partner Nilvera Status",
        related='partner_id.l10n_tr_nilvera_customer_status',
    )
    l10n_tr_ticarifatura_status = fields.Selection(
        selection=[
            ('pending', "Waiting Response"),
            ('approved', "Approved"),
            ('documentAnsweredAutomatically', "Approved Automatically"),
            ('rejected', "Rejected"),
        ],
        string="Commercial Response",
        readonly=True,
        copy=False,
        tracking=True,
    )
    l10n_tr_ticarifatura_response_note = fields.Text(
        string="Commercial Response Note",
        readonly=True,
        copy=False,
    )
    l10n_tr_ticarifatura_status_check_priority = fields.Integer(
        string="Commercial Status Check Priority",
        copy=False,
    )
    l10n_tr_nilvera_pdf_file = fields.Binary(
        attachment=True,
        string="Nilvera PDF File",
        copy=False,
    )
    l10n_tr_nilvera_pdf_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Nilvera PDF Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_tr_nilvera_pdf_id', 'l10n_tr_nilvera_pdf_file'),
        depends=['l10n_tr_nilvera_pdf_file'],
    )
    l10n_tr_original_invoice_date = fields.Date(string="Original Invoice Date")

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_gib_invoice_type", "l10n_tr_is_export_invoice")
    def _compute_l10n_tr_exemption_code_domain_list(self):
        for record in self:
            domain = []
            if record.l10n_tr_gib_invoice_type == "ISTISNA":
                domain.extend(("exception", "export_exception"))
            if record.l10n_tr_gib_invoice_type == "IHRACKAYITLI":
                domain.append("export_registration")
            if record.l10n_tr_is_export_invoice:
                domain.append("export_exception")
            record.l10n_tr_exemption_code_domain_list = domain

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_is_export_invoice")
    def _compute_l10n_tr_gib_invoice_type(self):
        for record in self:
            record.l10n_tr_gib_invoice_type = False

    @api.depends("l10n_tr_gib_invoice_scenario", "l10n_tr_gib_invoice_type", "partner_id")
    def _compute_l10n_tr_exemption_code_id(self):
        for record in self:
            record.l10n_tr_exemption_code_id = False

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

    def _l10n_tr_get_status_invoice_channel(self):
        self.ensure_one()
        return 'einvoice' if self.l10n_tr_is_export_invoice else self.partner_id.l10n_tr_nilvera_customer_status

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'TR1.2' in customization_id.text:
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def button_draft(self):
        # EXTENDS account
        for move in self.filtered('l10n_tr_nilvera_uuid'):
            if move.l10n_tr_nilvera_send_status == 'error':
                move.message_post(body=_("To preserve accounting integrity and comply with legal requirements, invoices cannot be reused once an error occurs. Please create a new invoice to continue."))
            elif move.l10n_tr_nilvera_send_status != 'not_sent' and not self.env.context.get('force_reset_sent_nilvera_move'):
                raise UserError(_("You cannot reset to draft an entry that has been sent to Nilvera."))
        super().button_draft()

    def _l10n_tr_nilvera_einvoice_check_invalid_invoice_reference(self):
        invalid_moves = self.env["account.move"]
        for record in self:
            _, parts = record._get_sequence_format_param(record.ref or "")
            if (
                record.move_type == "out_refund"
                and not record.reversed_entry_id
                and not (parts["prefix1"][:3] and parts["year"] and parts["seq"])
            ):
                invalid_moves |= record
        return invalid_moves

    def _l10n_tr_nilvera_check_invalid_type(self):
        invalid_invoices = self.env["account.move"]
        for record in self:
            if record.l10n_tr_gib_invoice_type in {"IADE", "TEVKIFATIADE"} ^ record.move_type == "out_refund":
                invalid_invoices |= record
        return invalid_invoices

    def _post(self, soft=True):
        for move in self:
            if move.l10n_tr_nilvera_send_status == 'error' and move.l10n_tr_nilvera_uuid:
                raise UserError(_("To preserve accounting integrity and comply with legal requirements, invoices cannot be reused once an error occurs. Please create a new invoice to continue."))
            if move.country_code == 'TR' and not move.l10n_tr_nilvera_uuid:
                move.l10n_tr_nilvera_uuid = str(uuid.uuid4())
        return super()._post(soft=soft)

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
        with _get_nilvera_client(self.env._, self.env.company) as client:
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
                error_message, error_codes = client._get_error_message_with_codes_from_response(response)

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
        for company, invoices in self.grouped("company_id").items():
            with _get_nilvera_client(self.env._, company) as client:
                for invoice in invoices:
                    invoice_channel = invoice._l10n_tr_get_status_invoice_channel()
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
                        elif nilvera_status == 'succeed' and invoice.move_type == 'out_invoice' and invoice.l10n_tr_gib_invoice_scenario == "TICARIFATURA":
                            if response.get('Answer') is None:
                                invoice.l10n_tr_ticarifatura_status = 'pending'
                            elif response['Answer'].get('AnswerCode') in {'approved', 'rejected', 'documentAnsweredAutomatically'}:
                                invoice.l10n_tr_ticarifatura_status = response['Answer']['AnswerCode']
                                invoice.l10n_tr_ticarifatura_response_note = response['Answer']['Description']
                    else:
                        invoice.message_post(body=_("The invoice status couldn't be retrieved from Nilvera."))

    def _l10n_tr_nilvera_get_documents(self, invoice_channel="einvoice", document_category="Purchase", journal_type="purchase"):
        with _get_nilvera_client(self.env._, self.env.company) as client:
            endpoint = f"/{invoice_channel}/{quote(document_category)}"
            last_fetched_date_field_name = f"l10n_tr_{invoice_channel}_{journal_type}_last_fetched_date"
            start_date = self.env.company[last_fetched_date_field_name]
            end_date = fields.Datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            page = 1

            # We filter documents by their CreatedDate on Nilvera, which represents when the document was created on
            # their platform. This ensures we always fetch the most recently uploaded documents, regardless of their
            # actual invoicing date (which might be much older).
            # The sorting allows us to resume from the last successfully fetched document in case an error interrupts
            # the batch fetching process.
            params = {
                'StatusCode': ['succeed'],
                'StartDate': start_date,
                'EndDate': end_date,
                'DateFilterType': 'CreatedDate',
                'SortColumn': 'CreationDateTime',
                'SortType': 'ASC',
            }
            response = client.request("GET", endpoint, params={**params, "Page": page})
            total_pages = response.get("TotalPages")
            if not total_pages:
                return

            moves = self.env['account.move']
            journal = self._l10n_tr_get_nilvera_invoice_journal(journal_type)
            while page <= total_pages:
                # Reuse first response, fetch subsequent pages.
                if page > 1:
                    response = client.request("GET", endpoint, params={**params, "Page": page})

                uuid_to_created_date = {
                    content.get('UUID'): content.get('CreatedDate')
                    for content in response.get('Content')
                }
                existing_document_uuids = {
                    rec['l10n_tr_nilvera_uuid'] for rec in self.env['account.move'].search_read(
                        [('l10n_tr_nilvera_uuid', 'in', list(uuid_to_created_date))],
                        ['l10n_tr_nilvera_uuid'],
                    )
                }
                for document_uuid, created_date in uuid_to_created_date.items():
                    # Skip invoices that have already been downloaded.
                    if document_uuid in existing_document_uuids:
                        continue
                    move = self._l10n_tr_nilvera_get_invoice_from_uuid(client, journal, document_uuid, document_category, invoice_channel)
                    self._l10n_tr_nilvera_add_pdf_to_invoice(client, move, document_uuid, document_category, invoice_channel)
                    moves |= move
                    # Update the last fetched date.
                    self.env.company.write({last_fetched_date_field_name: created_date[:19].replace('T', ' ')})
                    self.env.cr.commit()
                page += 1
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

        filename = f'{invoice.ref}.pdf' if invoice.ref else invoice._get_invoice_nilvera_pdf_report_filename()

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'res_id': invoice.id,
            'res_field': 'l10n_tr_nilvera_pdf_file',
            'res_model': 'account.move',
            'raw': base64.b64decode(response),
            'type': 'binary',
            'mimetype': 'application/pdf',
        })
        self.invalidate_recordset(fnames=["l10n_tr_nilvera_pdf_id", "l10n_tr_nilvera_pdf_file"])
        # The created attachement coming form Nilvera should be the main attachment
        invoice.message_main_attachment_id = attachment
        invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachment.ids)

    def l10n_tr_nilvera_get_pdf(self):
        with _get_nilvera_client(self.env._, self.env.company) as client:
            for invoice in self:
                if (
                        invoice.l10n_tr_nilvera_customer_status not in {'einvoice', 'earchive'}
                        or invoice.l10n_tr_nilvera_pdf_id
                        or invoice.l10n_tr_nilvera_send_status != 'succeed'
                ) and not self.env.context.get('rewrite_nilvera_pdf'):
                    continue
                self._l10n_tr_nilvera_add_pdf_to_invoice(
                    client,
                    invoice,
                    invoice.l10n_tr_nilvera_uuid,
                    document_category="Sale",
                    invoice_channel=invoice.l10n_tr_nilvera_customer_status,
                )

    def _l10n_tr_nilvera_einvoice_check_negative_lines(self):
        return any(
            line.display_type not in {'line_note', 'line_section'}
            and (line.quantity < 0 or line.price_unit < 0)
            for line in self.invoice_line_ids
        )

    def _get_partner_l10n_tr_nilvera_customer_alias_name(self):
        # Allows overriding the default customer alias with a custom one.
        self.ensure_one()
        return (
            self.l10n_tr_is_export_invoice
            and self.company_id.l10n_tr_nilvera_export_alias
            or self.partner_id.l10n_tr_nilvera_customer_alias_id.name
        )

    def _get_invoice_nilvera_pdf_report_filename(self):
        """ Get the filename of the Nilvera PDF invoice report. """
        self.ensure_one()
        return f"{self._get_move_display_name().replace(' ', '_').replace('/', '_')}_einvoice.pdf"

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

    def _cron_nilvera_get_sale_pdf(self, batch_size=100):
        """ Fetches the Nilvera generated PDFs for the sales generated on Odoo. """
        invoices_to_fetch_pdf = self.env['account.move'].search([
            ('l10n_tr_nilvera_send_status', '=', 'succeed'),
            ('move_type', '=', 'out_invoice'),
            ('l10n_tr_nilvera_pdf_file', '=', False),
        ], limit=batch_size)
        for company, invoices in invoices_to_fetch_pdf.grouped("company_id").items():
            with _get_nilvera_client(self.env._, company) as client:
                for invoice in invoices:
                    self._l10n_tr_nilvera_add_pdf_to_invoice(
                        client,
                        invoice,
                        invoice.l10n_tr_nilvera_uuid,
                        document_category="Sale",
                        invoice_channel=invoice.l10n_tr_nilvera_customer_status,
                    )

    def _get_starting_sequence(self):
        """
        Generate a valid name for credit notes.

        Nilvera requires invoice names in the format:
        <3 alphanumeric characters>/<year>/<sequence number>.

        When creating a credit note, an R is added by standard, so
        we remove the first letter of the journal prefix to make sure it
        remains 3 characters (e.g., RINV → RNV).
        """
        starting_sequence = super()._get_starting_sequence()
        if (
            self.company_id.country_id.code == "TR"
            and self.journal_id.refund_sequence
            and self.move_type in {"out_refund", "in_refund"}
        ):
            starting_sequence = starting_sequence[0] + starting_sequence[2:]
        return starting_sequence

    def _reverse_moves(self, default_values_list=None, cancel=False):
        if all(move.country_code != 'TR' or move.move_type != "out_invoice" for move in self):
            return super()._reverse_moves(default_values_list, cancel=cancel)

        if not default_values_list:
            default_values_list = [{}] * len(self)

        for default_vals, move in zip(default_values_list, self):
            if move.country_code != 'TR' or move.move_type != "out_invoice":
                continue
            line_vals = move.line_ids.copy_data()
            for line, vals in zip(move.line_ids, line_vals):
                vals.update(
                    {
                        "l10n_tr_original_line_id": line.id,
                        "l10n_tr_original_quantity": line.quantity,
                        "l10n_tr_original_tax_without_withholding": line.price_total - line.price_subtotal,
                    },
                )
            default_vals.update(
                {
                    'ref': move.name,
                    'l10n_tr_gib_invoice_scenario': 'TEMELFATURA',
                    'l10n_tr_gib_invoice_type': 'TEVKIFATIADE' if move.l10n_tr_gib_invoice_type == "TEVKIFAT" else "IADE",
                    'line_ids': [Command.create(vals) for vals in line_vals],
                },
            )

        return super()._reverse_moves(default_values_list, cancel=cancel)

    def l10n_tr_handle_409_error_for_send_answer(self, response):
        self.ensure_one()
        for error in response["Errors"]:
            if error.get("Code") in [1003, 1007, 1008, 1011]:
                self.l10n_tr_action_fetch_ticafatura_response()
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "message": _(
                            "Nilvera has already received a response for this invoice."
                            "\nThe latest response has been fetched and updated on the invoice.",
                        ),
                        "type": "warning",
                        # Reload the page to show the updated response.
                        "next": {
                            "type": "ir.actions.act_window",
                            "res_model": "account.move",
                            "res_id": self.id,
                            "view_mode": "form",
                            "views": [[False, "form"]],
                            "target": "current",
                        },
                    },
                }
        errors = [f"{error.get('Code')}: {error.get('Description')}" for error in response["Errors"]]
        raise ValidationError(_("Error sending request:\n%s", "\n".join(errors)))

    def l10n_tr_action_send_ticarifatura_response(self, answer_code="approved", rejection_note=""):
        """
        Send the Ticarifatura response to Nilvera.
        Applicable only for Commercial bills.

        :param str answer_code: 'approved' or 'rejected'
        :param str rejection_note: Note for rejection, if applicable.
        """
        self.ensure_one()
        if self.move_type != 'in_invoice' or self.l10n_tr_gib_invoice_scenario != 'TICARIFATURA':
            raise UserError(_("This action is only available for Commercial bills."))
        if self.l10n_tr_ticarifatura_status != 'pending':
            raise UserError(_("The response has already been sent for this bill."))

        with _get_nilvera_client(self.env._, self.env.company) as client:
            response = client.request(
                method="POST",
                endpoint="/einvoice/Purchase/SendAnswer",
                json={
                    "UUID": self.l10n_tr_nilvera_uuid,
                    "AnswerCode": answer_code,
                    "RejectNote": rejection_note,
                },
                handle_response=False,
            )

            if response.status_code == 200:
                self.l10n_tr_ticarifatura_status = answer_code
                self.l10n_tr_ticarifatura_response_note = rejection_note
            elif response.status_code in {401, 403}:
                raise UserError(_("Oops, seems like you're unauthorised to do this. Try another API key with more rights or contact Nilvera."))
            elif 403 < response.status_code < 600 and response.status_code != 409:
                raise UserError(
                    _(
                        "Odoo could not perform this action at the moment, try again later.\n"
                        "%(reason)s - %(status)s",
                        reason=response.reason,
                        status=response.status_code,
                    ),
                )
            elif response.status_code == 409:
                try:
                    decoded_response = response.json()
                except JSONDecodeError:
                    _logger.exception(_("Invalid JSON response: %s"), response.text)
                    raise UserError(_("An error occurred. Try again later."))
                return self.l10n_tr_handle_409_error_for_send_answer(decoded_response)
            return True

    def l10n_tr_action_fetch_ticafatura_response(self):
        """
        Fetch the Ticarifatura response status from Nilvera for the given UUID.
        Applicable only for Commercial Invoice.

        :param str uuid: The NILVERA UUID of the Commercial Invoice.
        """
        self.ensure_one()

        if self.move_type not in ['out_invoice', 'in_invoice'] or self.l10n_tr_gib_invoice_scenario != 'TICARIFATURA':
            raise UserError(_("This action is only available for Commercial Invoices/Bill."))
        if self.l10n_tr_ticarifatura_status != 'pending':
            if self.l10n_tr_nilvera_send_status != 'succeed':
                raise UserError(_("The invoice is not approved by Nilvera yet."))
            raise UserError(_("The response has already been received for this invoice."))

        with _get_nilvera_client(self.env._, self.env.company) as client:
            response = client.request(
                method="GET",
                endpoint=f"/einvoice/Purchase/{self.l10n_tr_nilvera_uuid}/Status",
            )
            if response.get("Answer") is not None:
                self.l10n_tr_ticarifatura_status = response["Answer"]["AnswerCode"]
                if response["Answer"].get("AnswerCode") == "rejected":
                    self.l10n_tr_ticarifatura_response_note = response["Answer"].get("Description")
                    self.with_context(rewrite_nilvera_pdf=True).l10n_tr_nilvera_get_pdf()
                    self.with_context(force_reset_sent_nilvera_move=True).button_draft()
                    self.button_cancel()

    def l10n_tr_action_approve_ticarifatura(self):
        self.ensure_one()
        return {
            'name': _('Accept Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_tr.ticafatura.response.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_response_code': 'approved',
            },
        }

    def l10n_tr_action_reject_ticarifatura(self):
        self.ensure_one()
        return {
            'name': _('Reject Bill'),
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_tr.ticafatura.response.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_move_id': self.id,
                'default_response_code': 'rejected',
            },
        }

    def _l10n_tr_nilvera_company_sync_ticarifatura_response(self, ratio=None, batch_size=20):
        for company in self.env.companies:
            if company.country_code != "TR" or not company.l10n_tr_nilvera_api_key:
                continue
            self.with_company(company)._cron_l10n_tr_nilvera_sync_ticarifatura_response(ratio, batch_size)

    def _cron_l10n_tr_nilvera_sync_ticarifatura_response(self, ratio=None, batch_size=20):
        """
        Sync the TICARIFATURA response status from Nilvera for Commercial Invoices in pending customer response.
        The sync will happen based on ratio of checked to unchecked invoices.
        If an invoice has been checked before, it will have a lower priority(Higher number) to be checked again.

        :param tuple ratio: A tuple of two integers representing the ratio of never checked and previously checked moves.
        :param int batch_size: The number of invoices to process in each batch.
        """
        _logger.info(_("Nilvera TICARIFATURA response sync started."))
        BASE_DOMAIN = [
                    ('move_type', 'in', ['out_invoice', 'in_invoice']),
                    ('l10n_tr_gib_invoice_scenario', '=', 'TICARIFATURA'),
                    ('l10n_tr_ticarifatura_status', '=', 'pending'),
                ]
        invoices_count = dict(
            self.env['account.move']._read_group(
                domain=BASE_DOMAIN,
                groupby=['l10n_tr_ticarifatura_status_check_priority'],
                aggregates=['id:count'],
            ),
        )
        never_checked_moves_count = invoices_count.get(0, 0)
        checked_moves_count = sum(count for priority, count in invoices_count.items() if priority > 0)

        if never_checked_moves_count + checked_moves_count == 0:
            _logger.info(_("No Commercial Invoices found for TICARIFATURA response sync."))
            return

        if ratio and sum(ratio) != 100:
            _logger.error("Invalid ratio value: %s. The sum of the two values must be 100.", ratio)
            ratio = None

        if not ratio:
            # Calculation the ratio to process data based on the count of checked and never checked moves.
            ratio = [0, 0]
            total = never_checked_moves_count + checked_moves_count
            ratio[0] = int((never_checked_moves_count * 100) / total)
            ratio[1] = int((checked_moves_count * 100) / total)

            diff = 100 - sum(ratio)
            if diff != 0:
                ratio[0] += diff

        # Calculate the total records to process of each type
        # Fetch the record and process
        # Avoiding fetching all records at once to prevent memory issues
        while never_checked_moves_count or checked_moves_count:
            # get invoices to check based on ratio and batch size
            never_checked_move_to_process_count = min((batch_size * (ratio[0] // 100)), never_checked_moves_count)
            checked_move_to_process_count = min((batch_size * (ratio[1] // 100)), checked_moves_count)

            # If total move count is less than batch size, adjust the counts
            if never_checked_move_to_process_count + checked_move_to_process_count < batch_size:
                remaining = batch_size - (never_checked_move_to_process_count + checked_move_to_process_count)

                max_take_from_checked = min(remaining, checked_moves_count - checked_move_to_process_count)
                checked_move_to_process_count += max_take_from_checked
                remaining -= max_take_from_checked

                # if still remaining, take from recently added moves
                max_take_from_unchecked = min(remaining, never_checked_moves_count - never_checked_move_to_process_count)
                never_checked_move_to_process_count += max_take_from_unchecked

                # Fetch and process new records frist
                if never_checked_move_to_process_count:
                    records = self.env['account.move'].search(
                        domain=BASE_DOMAIN + [('l10n_tr_ticarifatura_status_check_priority', '=', 0)],
                        order="create_date desc",
                        limit=never_checked_move_to_process_count,
                    )
                    for record in records:
                        record.l10n_tr_action_fetch_ticafatura_response()
                        record.write({"l10n_tr_ticarifatura_status_check_priority": record.l10n_tr_ticarifatura_status_check_priority + 1})
                        never_checked_moves_count -= 1

                # Fetch and process older records
                if checked_move_to_process_count:
                    records = self.env['account.move'].search(
                        domain=BASE_DOMAIN + [('l10n_tr_ticarifatura_status_check_priority', '>', 0)],
                        order='l10n_tr_ticarifatura_status_check_priority asc, create_date desc',
                        limit=checked_move_to_process_count,
                    )
                    for record in records:
                        record.l10n_tr_action_fetch_ticafatura_response()
                        record.write({"l10n_tr_ticarifatura_status_check_priority": record.l10n_tr_ticarifatura_status_check_priority + 1})
                        checked_moves_count -= 1
        _logger.info(_("Nilvera TICARIFATURA response sync completed."))
