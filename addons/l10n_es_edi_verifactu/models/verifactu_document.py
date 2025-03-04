from dateutil.relativedelta import relativedelta
from enum import Enum

import requests.exceptions

from odoo import _, api, Command, fields, models
from odoo.addons.l10n_es.models.http_adapter import PatchedHTTPAdapter
from odoo.exceptions import UserError


BATCH_LIMIT = 1000

# We store the errors as a language-independent code to avoid storing translated strings
# Document Errors
ERROR_NOTHING_TO_SEND = 'nothing_to_send'
ERROR_UNSUPPORTED_DOCUMENT_TYPE = 'unsupported_document_type'
ERROR_REQUEST_FAILED = 'request_failed'
ERROR_SOAPFAULT = 'soapfault'
# Parse Errors
ERROR_UNSUPPORTED_CONTENT_TYPE = 'unsupported_content_type'
ERROR_MALFORMED_RESPONSE = 'malformed_response'
ERROR_MALFORMED_RESPONSE_STATE = 'malformed_response_state'
# "Normal" Errors
ERROR_ACCESS_DENIED = 'access_denied'
ERROR_MALFORMED_DOCUMENT = 'malformed_document'


class L10nEsEdiVerifactuDocument(models.Model):
    """Veri*Factu Document
    It represents a Veri*Factu request to the AEAT (and eventually information about the received response).
    It i.e. ...
      * stores the XML we send
        * A Batch document basically just aggregates one or several "Veri*Factu Record Documents" ('l10n_es_edi_verifactu.record_document').
      * handles the sending to the AEAT
        * In case we can not send the document directly due to waiting time a cron is triggered at the next possible time.
      * and stores information about the received response (handled by the model "Veri*Factu Response Parser" / 'l10n_es_edi_verifactu.response_parser')
    Also see the docstring of the "Veri*Factu Record Mixin" for more details about the general flow.
    """
    _name = 'l10n_es_edi_verifactu.document'
    _description = "Veri*Factu Document"
    _order = 'response_time DESC NULLS FIRST, create_date DESC, id DESC'

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    document_type = fields.Selection(
        selection=[
            ('query', 'Query'),
            ('batch', 'Batch'),
        ],
        string='Document Type',
        required=True,
        readonly=True,
    )
    xml_attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="XML Attachment",
        copy=False,
        readonly=True,
    )
    # A batch is basically multiple records and a header
    record_document_ids = fields.One2many(
        comodel_name='l10n_es_edi_verifactu.record_document',
        inverse_name='document_id',
        string='Veri*Factu Records',
        readonly=True,
    )
    response_info = fields.Json(
        string="Response Info",
        readonly=True,
        copy=False,
        help="Technical Field providing information extracted from the response from the AEAT.",
    )
    response_message = fields.Text(
        copy=False,
        readonly=True,
        compute='_compute_l10n_es_edi_verifactu_fields_from_response_info',
        store=True,
    )
    response_time = fields.Datetime(
        string="Time of Response",
        readonly=True,
        help="The date and time on which we received the response (or tried to send in case of failure).",
        compute='_compute_l10n_es_edi_verifactu_fields_from_response_info',
        store=True,
    )
    state = fields.Selection(
        selection=[
            ('sending_failed', 'Sending Failed'),
            ('parsing_failed', 'Error while Parsing the Response'),
            ('rejected', 'Rejected'),
            ('registered_with_errors', 'Registered with Errors'),
            ('accepted', 'Accepted'),
        ],
        string='Status',
        compute='_compute_l10n_es_edi_verifactu_fields_from_response_info',
        store=True,
        help="""- Sending Failed: Tried to send to the AEAT but failed
                - Parsing Failed: There was an error while parsing the response from he AEAT
                - Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent record
                - Accepted: Registered by the AEAT without errors""",
    )

    @api.depends('document_type')
    def _compute_display_name(self):
        for document in self:
            document.display_name = document._get_attachment_filename()

    @api.depends('response_info')
    def _compute_l10n_es_edi_verifactu_fields_from_response_info(self):
        for document in self:
            info = document.response_info
            if not info:
                info = {
                    'response_message': False,
                    'response_time': False,
                    'state': False,
                }
            document.response_message = info['response_message']
            document.response_time = fields.Datetime.to_datetime(info['response_time'])
            document.state = info['state']

    def _add_attachment_from_xml(self, xml):
        self.ensure_one()
        attachment = self.env['ir.attachment'].create({
            'raw': xml,
            'name': self._get_attachment_filename(),
            'res_id': self.id,
            'res_model': self._name,
        })
        self.xml_attachment_id = attachment

    def _get_attachment_filename(self):
        self.ensure_one()
        document_type = 'consulta' if self.document_type == 'query' else 'remision'
        return f"verifactu_{self.id}_{document_type}.xml"

    @api.model
    def _create_batch_document(self, xml, record_documents):
        doc = self.create({
            'record_document_ids': [Command.set(record_documents.ids)],
            'document_type': 'batch',
        })
        doc._add_attachment_from_xml(xml)
        return doc

    @api.model
    def _record_identifier(self, company, name, invoice_date, amount_total_signed):
        """
        Return a dictionary with the values used to identify records in the Veri*Factu system.
          * 'IDEmisorFactura'
          * 'NumSerieFactura'
          * 'FechaExpedicionFactura'
          * 'ImporteTotal'; (only) needed for the QR code
            (See function `_compute_l10n_es_edi_verifactu_qr_code` of model 'l10n_es_edi_verifactu.record_mixin')
          * TODO: 'Huella' added during XML generation
        """
        errors = []

        if company:
            company_values = company._get_l10n_es_edi_verifactu_values()
            company_NIF = company_values['NIF']
            if not company_NIF or len(company_NIF) != 9:  # NIFType
                errors.append(_("The NIF '%(company_nif)s' of the company is not exactly 9 characters long",
                                company_nif=company_NIF))
        else:
            company_NIF = 'NO_DISPONIBLE'
            errors.append(_("The company is missing."))

        if not name or len(name) > 60:
            errors.append(_("The name of the record is not between 1 and 60 characters long: %(name)s",
                            name=name))

        if not invoice_date:
            invoice_date = 'NO_DISPONIBLE'
            errors.append(_("The invoice date is missing."))
        else:
            invoice_date = self.env['l10n_es_edi_verifactu.xml']._format_date_fecha_type(invoice_date)

        total_amount = self.env['l10n_es_edi_verifactu.xml']._round_format_number_2(amount_total_signed)

        return {
            'IDEmisorFactura': company_NIF,
            'NumSerieFactura': name,
            'FechaExpedicionFactura': invoice_date,
            'ImporteTotal': total_amount,
            'errors': errors,
        }

    @api.model
    def _get_record_key(self, record_identifier):
        # `record_identifier` is a dictionary like returned from function `_record_identifier`
        return str((record_identifier['IDEmisorFactura'], record_identifier['NumSerieFactura']))

    @api.model
    def _translate_error_tuple(self, error_tuple):
        error_type, error_message = error_tuple

        type_string = {
            ERROR_NOTHING_TO_SEND: _("There is no XML attachment to send."),
            ERROR_UNSUPPORTED_DOCUMENT_TYPE: _("The document type is currently not supported"),
            ERROR_REQUEST_FAILED: _("Sending the document to the AEAT failed"),
            ERROR_SOAPFAULT: _("The document was rejected by the AEAT"),
            ERROR_UNSUPPORTED_CONTENT_TYPE: _("We can not parse documents with that content type"),
            ERROR_MALFORMED_RESPONSE: _("The response could not be parsed"),
            ERROR_MALFORMED_RESPONSE_STATE: _("The state could not be determined from the response"),
            ERROR_ACCESS_DENIED: _("The document could not be sent; the access was denied"),
        }

        if error_type == ERROR_MALFORMED_DOCUMENT or error_type not in type_string:
            return error_message or _("Unknown error.")

        error_type_string = type_string[error_type]

        if error_message:
            return f"{error_type_string}: {error_message}"

        return error_type_string

    def _get_record_response_info(self, record_identifier):
        # `record_identifier` is a dictionary like returned from function `_record_identifier`
        self.ensure_one()

        record_key = self.env['l10n_es_edi_verifactu.document']._get_record_key(record_identifier)
        response_info = self.response_info or {'record_info': {}}

        record_info = response_info['record_info']
        record_response_info = None
        if record_info:
            # We expect an entry for `record_identifier`. If there is none we "build" an entry;
            # it indicates a parsing failure.
            record_response_info = record_info.get(record_key, None)
            if record_response_info is None:
                record_response_info = {
                    'state': 'parsing_failed',
                    'errors': [(None, _("We could not find any information about the record in the linked batch document."))],
                }
            record_response_info['level'] = 'record'
        else:
            # I.e. in case of soapfault and access denied there is no `record_info`.
            # So we just return the global 'state' / 'errors'
            record_response_info = {
                'state': response_info['state'],
                'errors': response_info['errors'],
                'level': 'document',
            }

        # The errors are stored as tuples to avoid storing translated values.
        # We translate / stringify them here.
        translated_errors = [
            self._translate_error_tuple(error) for error in record_response_info['errors']
        ]
        record_response_info['errors'] = translated_errors
        return record_response_info

    @api.model
    def _create_batch_and_send(self, record_documents):
        document = record_documents.with_company(self.env.company)._create_batch_document()
        document._send()

        if self.env['account.move']._can_commit():
            self._cr.commit()

        if document.state == 'sending_failed':
            cron = self.env.ref('l10n_es_edi_verifactu.cron_verifactu_batch', raise_if_not_found=False)
            if cron:
                cron._trigger(at=fields.Datetime.now() + relativedelta(seconds=60))

        return document

    @api.model
    def get_time_for_next_batch(self, company):
        # TODO: just put a field on the company?
        last_document = self.sudo().search([
            ('company_id', '=', company.id),
            ('state', 'not in', [False, 'sending_failed']),
            ('response_time', '!=', False),
        ], order=self._order, limit=1)
        if last_document:
            # In case of rejection due to soap fault we get no waiting_time_seconds.
            # 60 seconds is the default value mentioned in the documentation
            seconds_to_wait = last_document.response_info.get('waiting_time_seconds') or 60
            return last_document.response_time + relativedelta(seconds=seconds_to_wait)
        return False

    @api.model
    def trigger_next_batch(self):
        """
        1. Resend all documents that we failed to send previously.
        2. Send all waiting record documents that we can send.
        3. Trigger the cron again at a later date to send the record documents we could not send
        """
        # TODO: cron handling; maybe 1 cron per company better?

        documents_to_resend = self.env['l10n_es_edi_verifactu.document'].sudo().search([
            ('state', '=', 'sending_failed')
        ])
        for document in documents_to_resend:
            document._send()
            if document.state == 'sending_failed':
                cron = self.env.ref('l10n_es_edi_verifactu.cron_verifactu_batch', raise_if_not_found=False)
                if cron:
                    cron._trigger(at=fields.Datetime.now() + relativedelta(seconds=60))

        record_documents_per_company = self.env['l10n_es_edi_verifactu.record_document']._read_group(
            [('document_id', '=', False)],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        )

        if not record_documents_per_company:
            return

        for company, record_documents in record_documents_per_company:
            # We sort the `record_documents` to batch them in the order they were chained (`create_date`).
            # TODO: explicitly sorting by `create_date` may be better
            record_documents = record_documents.sorted(reverse=True)

            # Send batches with size BATCH_LIMIT; they are not restricted by the waiting time
            record_count = len(record_documents)
            start_index = 0
            end_index = min(record_count, start_index + BATCH_LIMIT)
            while end_index - start_index == BATCH_LIMIT:
                self.with_company(company)._create_batch_and_send(record_documents[start_index:end_index])
                start_index += BATCH_LIMIT
                end_index = min(record_count, start_index + BATCH_LIMIT)
            remaining_records = record_documents[start_index:]

            if not remaining_records:
                continue

            next_batch_time = self.get_time_for_next_batch(company)
            if not next_batch_time or fields.Datetime.now() >= next_batch_time:
                self.with_company(company)._create_batch_and_send(remaining_records)
            else:
                cron = self.env.ref('l10n_es_edi_verifactu.cron_verifactu_batch', raise_if_not_found=False)
                if cron:
                    cron._trigger(at=next_batch_time)

    def _request(self):
        self.ensure_one()
        company = self.company_id

        session = requests.Session()
        session.cert = company.l10n_es_edi_verifactu_certificate_id
        session.mount("https://", PatchedHTTPAdapter())

        soap_xml = self.env['l10n_es_edi_verifactu.xml']._build_soap_request_xml(self.xml_attachment_id.raw)

        response = session.request(
            'post',
            url=company.l10n_es_edi_verifactu_endpoints['verifactu'],
            data=soap_xml,
            timeout=15,
            headers={"Content-Type": 'application/soap+xml;charset=UTF-8'},
        )

        return response

    def _send_request(self):
        self.ensure_one()

        info = {
            'errors': [],
            'response': None,
            'response_message': False,
            'response_time': False,
        }

        if not self.xml_attachment_id.raw:
            info['errors'].append((ERROR_NOTHING_TO_SEND, None))
            info['state'] = 'sending_failed'
            return info

        if self.document_type not in ('batch', 'query'):
            info['errors'].append((ERROR_UNSUPPORTED_DOCUMENT_TYPE, None))
            info['state'] = 'sending_failed'
            return info

        try:
            response = self._request()
            info['response'] = response
            info['response_message'] = response.text
        except requests.exceptions.RequestException as e:
            info['errors'].append((ERROR_REQUEST_FAILED, f"{e}"))
            info['state'] = 'sending_failed'
        info['response_time'] = fields.Datetime.to_string(fields.Datetime.now())

        return info

    def _had_incident(self):
        self.ensure_one()
        # TODO: also in case we send much later than next batch time?
        return self.state == 'sending_failed'

    def _send(self):
        self.ensure_one()

        if self._had_incident():
            # We send or even resend, but we need to set a flag in the XML
            # TODO: regenerate XML / update XML for Incidencia
            pass
        elif self.response_time:
            # Do not resend other documents
            return

        info = self._send_request()

        response = info['response']
        if response:
            parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type=self.document_type)
            info['errors'].extend(parse_info.pop('errors', []))
            info.update(parse_info)

        if 'state' not in info:
            info['errors'].append((ERROR_MALFORMED_RESPONSE_STATE, None))
            info['state'] = 'parsing_failed'

        # remove non-serializable values
        info.pop('xml_tree', None)
        info.pop('html_tree', None)
        info.pop('response', None)
        self.response_info = info

        return info

    @api.ondelete(at_uninstall=False)
    def _never_unlink_sent_documents(self):
        if self.state:
            raise UserError(_("You cannot delete Veri*Factu documents that have been sent or failed to sent to the AEAT."))
