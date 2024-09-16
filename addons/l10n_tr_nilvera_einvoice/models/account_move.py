import base64, uuid
from markupsafe import Markup

from odoo import api, fields, models, _


class AccountMove(models.Model):
    _name = 'account.move'
    _inherit = ['account.move']

    def _default_l10n_tr_nilvera_uuid(self):
        return str(uuid.uuid4())

    l10n_tr_nilvera_einvoice_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Facturae Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_tr_nilvera_einvoice_xml_id',
                                                                'l10n_tr_nilvera_einvoice_xml_file'),
        depends=['l10n_tr_nilvera_einvoice_xml_file']
    )
    l10n_tr_nilvera_einvoice_xml_file = fields.Binary(
        attachment=True,
        string="Facturae File",
        copy=False,
    )
    l10n_tr_nilvera_uuid = fields.Char(
        string='Document UUID (TR)',
        copy=False,
        readonly=True,
        default=_default_l10n_tr_nilvera_uuid,
        help="Universally unique identifier of the Invoice",
    )

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        customization_id = tree.find('{*}CustomizationID')
        if customization_id is not None and 'TR1.2' in customization_id.text:
            return self.env['account.edi.xml.ubl.tr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def _l10n_tr_nilvera_submit_einvoice(self, xml_file, customer_alias):
        self._l10n_tr_nilvera_submit_document(
            xml_file=xml_file,
            endpoint=f"/einvoice/Send/Xml?Alias={customer_alias}",
            success_message=_("The invoice has been successfully sent to Nilvera as an E-Invoice."),
            post_series_func=self._l10n_tr_nilvera_post_einvoice_series,
        )

    def _l10n_tr_nilvera_submit_earchive(self, xml_file):
        self._l10n_tr_nilvera_submit_document(
            xml_file=xml_file,
            endpoint="/earchive/Send/Xml",
            success_message=_("The invoice has been successfully sent to Nilvera as an E-Arhive."),
            post_series_func=self._l10n_tr_nilvera_post_earchive_series,
        )

    def _l10n_tr_nilvera_submit_document(self, xml_file, endpoint, success_message, post_series_func):
        """Generic function to handle e-invoice and e-archive submissions to Nilvera."""
        client = self.env.company._get_nilvera_client()
        response = client.request(
            "POST",
            endpoint,
            files={'file': (xml_file.name, xml_file, 'application/xml')},
            handle_response=False,
        )

        msg = ""

        if response.status_code == 200:
            msg = success_message
        elif 400 <= response.status_code < 500:
            error_message, error_codes = self._l10n_tr_nilvera_einvoice_get_error_messages_from_response(response)

            if 3009 in error_codes: # If the sequence/series is not found on Nilvera, add it then retry.
                post_series_func()
                return self._l10n_tr_nilvera_submit_document(xml_file, endpoint, success_message, post_series_func)

            msg += error_message

        self.message_post(body=Markup(msg))

    def _l10n_tr_nilvera_post_einvoice_series(self):
        self._l10n_tr_nilvera_post_series("/einvoice/Series")

    def _l10n_tr_nilvera_post_archive_series(self):
        self._l10n_tr_nilvera_post_series("/earchive/Series")

    def _l10n_tr_nilvera_post_series(self, endpoint):
        client = self.env.company._get_nilvera_client()
        series = self.sequence_prefix.split('/')[0]
        client.request(
            "POST",
            endpoint,
            json={
                'Name': series,
                'IsActive': True,
                'IsDefault': False,
            },
        )

    def _l10n_tr_nilvera_get_documents(self):
        """
        1- get the client
        2- call the api for purchase
        3- map the uuids and call the api for purchase/xml or pdf?
        4- parse em and parse em well
        """
        client = self.env.company._get_nilvera_client()
        response = client.request(
            "GET",
            "/einvoice/Purchase",
        )

        if response.get('Content'):
            document_uuids = [content.get('UUID') for content in response.get('Content')]

            for document_uuid in document_uuids:
                move = self._l10n_tr_nilvera_get_invoice_from_uuid(client, document_uuid)
                self._l10n_tr_nilvera_add_pdf_to_invoice(client, move, document_uuid)

    def _l10n_tr_nilvera_get_invoice_from_uuid(self, client, document_uuid):
        response = client.request(
            "GET",
            f"/einvoice/Purchase/{document_uuid}/xml",
        )

        journal = self.env.company.l10n_tr_nilvera_purchase_journal_id
        if not journal:
            journal = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.env.company),
                ('type', '=', 'purchase')
            ], limit=1)

        filename = 'attachment'

        attachment_vals = {
            'name': f'{filename}.xml',
            'raw': response,
            'type': 'binary',
            'mimetype': 'application/xml',
        }

        try:
            attachment = self.env['ir.attachment'].create(attachment_vals)
            move = journal.with_context(
                default_move_type='in_invoice',
                default_l10n_tr_nilvera_uuid=uuid,
            )._create_document_from_attachment(attachment.id)
            move._message_log(body=_('Nilvera document has been received successfully'))
        # pylint: disable=broad-except
        except Exception:
            # If the invoice creation fails, create an empty invoice with the attachment. The PDF will be
            # added in a later step as well.
            move = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'company_id': self.env.company.id,
                'l10n_tr_nilvera_uuid': uuid,
            })
            attachment_vals.update({
                'res_model': 'account.move',
                'res_id': move.id,
            })
            self.env['ir.attachment'].create(attachment_vals)

        return move
    
    def _l10n_tr_nilvera_add_pdf_to_invoice(self, client, invoice, document_uuid):
        response = client.request(
            "GET",
            f"/einvoice/Purchase/{document_uuid}/pdf",
        )

        attachment = self.env['ir.attachment'].create({
            'name': 'attachment',
            'res_id': invoice.id,
            'res_model': 'account.move',
            'datas': response + '=' * (len(response) % 3),  # Fix incorrect padding
            'type': 'binary',
            'mimetype': 'application/pdf',
        })

        if invoice.message_main_attachment_id and \
                invoice.message_main_attachment_id.name.endswith('.xml') and \
                'pdf' not in invoice.message_main_attachment_id.mimetype:
            invoice.message_main_attachment_id = attachment
        invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachment.ids)

    def _l10n_tr_nilvera_einvoice_get_error_messages_from_response(self, response):
        msg = ""
        error_codes = []

        response_json = response.json()
        if errors := response_json.get('Errors'):
            msg += _("The invoice couldn't be sent due to the following errors:<br/>")
            for error in errors:
                msg += "<br/>".join("%s - %s" % (error.get('Code'), error.get('Description')))
                error_codes.append(error.get('Code'))

        return msg, error_codes

    def _l10n_tr_nilvera_einvoice_get_default_enable(self):
        self.ensure_one()
        return not self.invoice_pdf_report_id \
            and not self.l10n_tr_nilvera_einvoice_xml_id \
            and self.is_invoice(include_receipts=True) \
            and self.company_id.country_code == 'TR' \
            # and invoice not sent before

    def _l10n_tr_nilvera_einvoice_get_filename(self):
        self.ensure_one()
        return '%s_einvoice.xml' % self.name.replace("/", "_")

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_nilvera_get_new_documents(self):
        self._l10n_tr_nilvera_get_documents()
