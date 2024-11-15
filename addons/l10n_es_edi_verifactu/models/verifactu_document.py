import datetime
import re
import requests.exceptions

from dateutil.relativedelta import relativedelta

from odoo import _, api, Command, fields, models
from odoo.addons.l10n_es.models.http_adapter import PatchedHTTPAdapter


BATCH_LIMIT = 1000


class L10nEsEdiVerifactuDocument(models.Model):
    _name = 'l10n_es_edi_verifactu.document'
    _description = "Document object representing a Veri*Factu XML"
    _order = 'response_time DESC, create_date DESC, id DESC'

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        required=True,
    )
    document_type = fields.Selection(
        selection=[
            ('record', 'Record'),
            ('query', 'Query'),
            ('batch', 'Batch'),
        ],
        string='Document Type',
        required=True,
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
    )
    response_message = fields.Text(
        copy=False,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('sending_failed', 'Sending Failed'),
            ('registered_with_errors', 'Registered with Errors'),
            ('accepted', 'Accepted'),
            ('rejected', 'Rejected'),
        ],
        string='Status',
        copy=False,
    )
    response_time = fields.Datetime(
        string="Time of Response",
        readonly=True,
        copy=False,
        help="The date and time on which we received the response.",  # Also set in case of failure
    )
    response_info = fields.Json(
        string="Response Info",
        readonly=True,
        copy=False,
        help="Technical Field providing information extracted from the response from the AEAT.",
    )

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
        name = f"{self.id}"
        sanitized_name = re.sub(r'[\W_]', '', name)  # remove non-word char or underscores
        return f"verifactu_{sanitized_name}_{self.document_type}.xml"

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
    def _create_batch_and_send(self, record_documents):
        # For the cron we specifically set the `self.env.company`
        batch_xml, batch_errors = record_documents.with_company(self.env.company)._create_batch_xml()
        if batch_errors:
            return

        document = self.env['l10n_es_edi_verifactu.document']._create_batch_document(batch_xml, record_documents)
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
        2. Send all waiting record documents.
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


        record_document_domain = [
            ('state', '=', False),
        ]
        record_documents_per_company = self.env['l10n_es_edi_verifactu.record_document']._read_group(
            record_document_domain, ['company_id'], ['id:recordset']
        )

        if not record_documents_per_company:
            return

        for company, record_documents in record_documents_per_company:
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
        }

        if not self.xml_attachment_id.raw:
            info['errors'].append("There is nothing to send.")
            info['state'] = 'sending_failed'
            return info

        if self.document_type not in ('batch', 'query'):
            info['errors'].append("Sending the Veri*Factu document not implemented for the document type.")
            info['state'] = 'sending_failed'
            return info

        try:
            info['response'] = self._request()
        except requests.exceptions.RequestException as e:
            info['errors'].append(f"Sending the Veri*Factu document to the AEAT failed: {e}")
            info['state'] = 'sending_failed'
        info['response_time'] = datetime.datetime.utcnow()

        return info

    def _send(self):

        info = self._send_request()
        self.response_time = info.pop('response_time', False)

        response = info['response']
        if response:
            self.response_message = response.text
            parse_info = self.env['l10n_es_edi_verifactu.response_parser']._parse_response(response, document_type=self.document_type)
            info['errors'].extend(parse_info.pop('errors', []))
            info.update(parse_info)

        if 'state' not in info:
            info['errors'].append(_('The state could not be determined from the response.'))
            info['state'] = False

        self.state = info['state']

        # remove non-serializable values
        info.pop('xml_tree', None)
        info.pop('html_tree', None)
        info.pop('response', None)
        self.response_info = info

        return info
