from datetime import datetime, timedelta
from pytz import timezone
from werkzeug.urls import url_quote_plus, url_encode

import contextlib
import hashlib
import math
import requests.exceptions
import json

from odoo import _, api, fields, models
from odoo.addons.l10n_es.models.http_adapter import PatchedHTTPAdapter
from odoo.exceptions import UserError
from odoo.tools import float_repr, float_round, zeep

import odoo.release


VERIFACTU_VERSION = "1.0"

BATCH_LIMIT = 1000


def _sha256(string):
    hash_string = hashlib.sha256(string.encode('utf-8'))
    return hash_string.hexdigest().upper()


class L10nEsEdiVerifactuDocumentParseError(Exception):
    pass


class L10nEsEdiVerifactuDocument(models.Model):
    """Veri*Factu Document
    It represents a billing record with the necessary data specified by the AEAT.
    It i.e. ...
      * stores the data as JSON
      * handles the sending of the data as XML to the AEAT
      * stores information extracted from the received response

    The main function to generate Veri*Factu Documents is `_mark_records_for_next_batch`:
      1. It generates the documents (submission or cancellation)
         * The documents form a chain in generation order by including a reference to the preceding document.
         * The function handles the correct chaining.
      2. It sends them (and any other unsent documents) directly to the AEAT if possible (see below).

    We can not necessarily send the documents directly after generation.
    This is because the AEAT requires a waiting time between shipments (or reaching 1000 new records to send).
    The waiting time is usually 60 seconds.
    In case we cannot send the records directly a cron will be triggered at the next possible time.

    Note that (succesfully generated) Documents can not be deleted.
    This is since the Documents form a chain (in generation order) by including a reference to the preceding document.
    The chain also includes documents that are (/ possibly will be) rejected by the AEAT.
    """
    _name = 'l10n_es_edi_verifactu.document'
    _description = "Veri*Factu Document"
    _order = 'create_date DESC, id DESC'

    company_id = fields.Many2one(
        string="Company",
        comodel_name='res.company',
        required=True,
        readonly=True,
    )
    move_id = fields.Many2one(
        string="Journal Entry",
        comodel_name='account.move',
        readonly=True,
    )
    chain_index = fields.Integer(
        string="Chain Index",
        copy=False,
        readonly=True,
        help="Index in the chain of Veri*Factu Documents. It is only set if the generation was succesful.",
    )
    record_identifier = fields.Json(
        string="Veri*Factu Record Identifier",
        help="Technical field containing the values used to identify records in the Veri*Factu system.",
        readonly=True,
    )
    document_type = fields.Selection(
        string="Document Type",
        selection=[
            ('submission', "Submission"),
            ('cancellation', "Cancellation"),
        ],
        readonly=True,
        required=True,
    )
    json_attachment_id = fields.Many2one(
        string="JSON Attachment",
        comodel_name='ir.attachment',
        readonly=True,
    )
    json_attachment_filename = fields.Char(
        string="JSON Filename",
        compute='_compute_json_attachment_filename',
    )
    # To use the 'binary' widget in the form view to download the attachment
    json_attachment_base64 = fields.Binary(
        string="JSON Attachment (Base64)",
        related='json_attachment_id.datas',
    )
    errors = fields.Html(
        string="Errors",
        copy=False,
        readonly=True,
    )
    response_csv = fields.Char(
        string="Response CSV",
        help="The CSV of the response from the tax agency. There may not be one in case all documents of the batch were rejected.",
        copy=False,
        readonly=True,
    )
    state = fields.Selection(
        string="Status",
        selection=[
            ('rejected', "Rejected"),
            ('registered_with_errors', "Registered with Errors"),
            ('accepted', "Accepted"),
        ],
        help="""- Rejected: Successfully sent to the AEAT, but it was rejected during validation
                - Registered with Errors: Registered at the AEAT, but the AEAT has some issues with the sent record
                - Accepted: Registered by the AEAT without errors""",
        copy=False,
        readonly=True,
    )

    @api.depends('document_type')
    def _compute_display_name(self):
        for document in self:
            document.display_name = _("Verifactu Document %s", document.id)

    @api.depends('document_type')
    def _compute_json_attachment_filename(self):
        for document in self:
            document_type = 'annulacion' if document.document_type == 'cancellation' else 'alta'
            name = f"verifactu_registro_{document.id}_{document_type}.json"
            document.json_attachment_filename = name

    def _get_document_dict(self):
        self.ensure_one()
        json_data = self.json_attachment_id.raw.decode()
        return json.loads(json_data)

    @api.model
    def _format_errors(self, title, errors):
        error = {
            'error_title': title,
            'errors': errors,
        }
        return self.env['account.move.send']._format_error_html(error)

    @api.model
    def _check_record_values(self, vals):
        errors = []

        company = vals['company']

        company_values = company._l10n_es_edi_verifactu_get_values()
        company_NIF = company_values['NIF']
        if not company_NIF or len(company_NIF) != 9:  # NIFType
            errors.append(_("The NIF '%(company_NIF)s' of the company is not exactly 9 characters long.",
                            company_NIF=company_NIF))

        name = vals['name']
        if not name or len(name) > 60:
            errors.append(_("The name of the record is not between 1 and 60 characters long: %(name)s.",
                            name=name))

        certificate = company.sudo()._l10n_es_edi_verifactu_get_certificate()
        if not certificate:
            errors.append(_("There is no certificate configured for Veri*Factu on the company."))

        invoice_date = vals['invoice_date']
        if not invoice_date:
            errors.append(_("The invoice date is missing."))

        move_type = vals['move_type']
        if move_type not in ['out_invoice', 'out_refund']:
            errors.append(_("The record has to be an invoice or a credit note."))

        verifactu_tax_type = vals['verifactu_tax_type']
        tax_details = vals['tax_details']
        sujeto_tax_types = self.env['account.tax']._l10n_es_get_sujeto_tax_types()
        ignored_tax_types = ['ignore', 'retencion']
        supported_tax_types = sujeto_tax_types + ignored_tax_types + ['no_sujeto', 'no_sujeto_loc', 'recargo', 'exento']
        tax_type_description = self.env['account.tax']._fields['l10n_es_type'].get_description(self.env)
        if not tax_details['tax_details']:
            errors.append(_("There are no taxes set on the invoice"))
        for tax_detail in tax_details['tax_details'].values():
            tax_type = tax_detail['l10n_es_type']
            if tax_type not in supported_tax_types:
                # tax_type in ('no_deducible', 'dua')
                # The remaining tax types are purchase taxes (for vendor bills).
                errors.append(_("A tax with value '%(tax_type)s' as %(field)s is not supported.",
                                field=tax_type_description['string'],
                                tax_type=dict(tax_type_description['selection'])[tax_type]))
            elif tax_type in ('no_sujeto', 'no_sujeto_loc') and verifactu_tax_type == '01':
                tax_percentage = tax_detail['amount']
                tax_amount = tax_detail['tax_amount']
                if float_round(tax_percentage, precision_digits=2) or float_round(tax_amount, precision_digits=2):
                    errors.append(_("No Sujeto VAT taxes must have 0 amount."))
            if len(tax_detail['recargo_taxes']) > 1:
                errors.append(_("Only a single recargo tax may used per \"main\" tax."))

        verifactu_tax_types = {
            tax_detail['verifactu_tax_type']
            for tax_detail in tax_details['tax_details'].values()
            if tax_detail['is_main_tax']
        }
        if len(verifactu_tax_types) > 1:
            name_map = self.env['account.tax']._l10n_es_edi_verifactu_get_tax_types_name_map()
            human_readable_types = [name_map[t] for t in verifactu_tax_types]
            errors.append(_("We only allow a single Veri*Factu Tax Type per document: %(types)s.",
                            types=', '.join(human_readable_types)))

        for record_detail in tax_details['tax_details_per_record'].values():
            main_tax_details = [tax_detail for key, tax_detail in record_detail['tax_details'].items() if key['is_main_tax']]
            if len(main_tax_details) > 1 or any(len(tax_detail['group_tax_details']) > 1 for tax_detail in main_tax_details):
                errors.append(_("We only allow a single \"main\" tax per line."))
                # Giving the errors once should be enough
                break

        return errors

    def _create_for_record(self, record_values, previous_record_identifier=None):
        """Note: In case we succesfully create a JSON we delete all linked documents that failed the JSON creation."""
        company = record_values['company']
        document_vals = record_values['document_vals']
        generation_errors = record_values['errors']

        json_string = None
        if generation_errors:
            error_title = _("The Veri*Factu document could not be created")
            document_vals['errors'] = self._format_errors(error_title, generation_errors)
        else:
            render_vals = self._render_vals(
                record_values, previous_record_identifier=previous_record_identifier,
            )
            # We do not allow generating documents that would change the record identifier (i.e. values in the QR code)
            record_identifier = render_vals['record_identifier']
            old_record_identifier = record_values['record_identifier']
            if old_record_identifier:
                keys_to_check = ['IDEmisorFactura', 'NumSerieFactura', 'FechaExpedicionFactura', 'ImporteTotal']
                changed_identifiers = {
                    key: (old_record_identifier[key], record_identifier[key])
                    for key in keys_to_check
                    if old_record_identifier[key] != record_identifier[key]
                }
                if changed_identifiers:
                    error_title = _("The Veri*Factu document was not created")
                    errors = [_("The record identifier changed: %(key)s (%(old)s → %(new)s)",
                                key=key, old=old, new=new)
                              for key, (old, new) in changed_identifiers.items()]
                    document_vals['errors'] = self._format_errors(error_title, errors)
            if not document_vals.get('errors'):
                document_dict = {render_vals['record_type']: render_vals[render_vals['record_type']]}
                json_string = json.dumps(document_dict)
                document_vals.update({
                    'record_identifier': record_identifier,
                    'chain_index': company._l10n_es_edi_verifactu_get_next_chain_index(),
                })

        document = self.create(document_vals)

        if json_string:
            record = record_values['record']
            document.json_attachment_id = self.env['ir.attachment'].create({
                'raw': json_string,
                'name': document.json_attachment_filename,
                'res_id': record.id,
                'res_model': record._name,
                'mimetype': 'application/json',
            })
            record_values['documents'].filtered(lambda rd: not rd.json_attachment_id).unlink()

        return document

    def _mark_records_for_next_batch(self, record_values_list):
        """Create Veri*Factu documents for input `record_values_list`.
        Return a dictionary (record -> document) containing all the created documents.
        In case we already have documents waiting to be sent for a record it is skipped (no new document is created).
        The documents are also created in case the JSON generation fails; to inspect the errors.
        Such documents are deleted in case the JSON generation succeeds for a record at a later time (see `_create_for_record`).
        :param list record_values_list: list of record values dictionaries (to be passed to `_create_for_record`)
        """
        result = {}

        # Group the records per company
        grouped_record_values_list = {}
        for record_values in record_values_list:
            company = record_values['company']
            grouped_record_values_list.setdefault(company, []).append(record_values)

        for company, company_record_values_list in grouped_record_values_list.items():
            # We chain all the created documents per company in generation order.
            # Thus we can not generate multiple documents for the same company at the same time.
            # We use `company.l10n_es_edi_verifactu_chain_sequence_id` to
            #   * explicitly number the documents in order
            #   * prevent the concurrent creation of documents (see the following code block)
            try:
                chain_sequence = company.l10n_es_edi_verifactu_chain_sequence_id
                self.env['res.company']._with_locked_records(chain_sequence)
            except UserError:
                continue

            previous_document = self.env['l10n_es_edi_verifactu.document'].search(
                [('chain_index', '!=', False)], order='chain_index desc', limit=1,
            )
            for record_values in record_values_list:
                if record_values.get('documents', self.env[self._name])._filter_waiting():
                    continue
                document = self.env['l10n_es_edi_verifactu.document']._create_for_record(
                    record_values, previous_record_identifier=previous_document.record_identifier,
                )
                if document.state != 'error':
                    previous_document = document
                result[record_values['record']] = document
        self.env['l10n_es_edi_verifactu.document'].trigger_next_batch()
        return result

    @api.model
    def trigger_next_batch(self):
        """
        1. Send all waiting documents that we can send
        2. Trigger the cron again at a later date to send the documents we could not send
        """
        unsent_domain = [
            ('json_attachment_id', '!=', False),
            ('state', '=', False),
        ]
        documents_per_company = self._read_group(
            unsent_domain,
            groupby=['company_id'],
            aggregates=['id:recordset'],
        )

        if not documents_per_company:
            return

        next_trigger_time = None
        for company, documents in documents_per_company:
            # Avoid sending a document twice due to concurrent calls to `trigger_next_batch`
            # TODO: Maybe lock the whole company (or sth verifactu specific on the company; or the whole cron) to be safe
            try:
                self.env['res.company']._with_locked_records(documents)
            except UserError:
                # We will later make sure that we trigger the cron again
                continue

            # We choose the language since this function may be executed on the cron.
            langs = documents.create_uid.mapped('lang')
            lang = 'es_ES' if 'es_ES' in langs else langs[0]
            # We sort the `documents` to batch them in the order they were chained
            documents = documents.sorted('chain_index').with_context(lang=lang)

            # Send batches with size BATCH_LIMIT; they are not restricted by the waiting time
            next_batch = documents[0:BATCH_LIMIT]
            start_index = 0
            while len(next_batch) == BATCH_LIMIT:
                next_batch.with_company(company)._send_as_batch()
                start_index += BATCH_LIMIT
                next_batch = documents[start_index:start_index + BATCH_LIMIT]
            # Now: len(next_batch) < BATCH_LIMIT ; we need to respect the waiting time

            if not next_batch:
                continue

            next_batch_time = company.l10n_es_edi_verifactu_next_batch_time
            if not next_batch_time or fields.Datetime.now() >= next_batch_time:
                next_batch.with_company(company)._send_as_batch()
            else:
                # Since we have a `next_batch_time` the `next_trigger_time` will be set to a datetime
                # We set it to the minimum of all the already encountered `next_batch_time`
                next_trigger_time = min(next_trigger_time or datetime.max, next_batch_time)

        # In case any of the documents were not successfully sent we trigger the cron again in 60s
        # (or at the next batch time if the 60s is earlier)
        for company, documents in documents_per_company:
            unsent_documents = documents.filtered_domain(unsent_domain)
            next_batch_time = company.l10n_es_edi_verifactu_next_batch_time
            if unsent_documents:
                # Trigger in 60s or at the next batch time (except if there is an earlier trigger already)
                in_60_seconds = fields.Datetime.now() + timedelta(seconds=60)
                company_next_trigger_time = max(in_60_seconds, next_batch_time or datetime.min)
                # Set `next_trigger_time` to the minimum of all the already encountered trigger times
                next_trigger_time = min(next_trigger_time or datetime.max, company_next_trigger_time)

        if next_trigger_time:
            cron = self.env.ref('l10n_es_edi_verifactu.cron_verifactu_batch', raise_if_not_found=False)
            if cron:
                cron._trigger(at=next_trigger_time)

    @api.model
    def _get_zeep_operations(self, operation):
        """The creation of the zeep client may raise (in case of networking issues)."""
        company = self.env.company

        session = requests.Session()

        settings = zeep.Settings(forbid_entities=False, strict=False)
        wsdl = company._l10n_es_edi_verifactu_get_endpoints()['wsdl']
        client = zeep.Client(
            wsdl['url'], session=session, settings=settings,
            operation_timeout=60, timeout=60,
        )

        # Note: using the "certificate" before creating `client` causes an error during the `client` creation
        session.cert = company.sudo()._l10n_es_edi_verifactu_get_certificate()
        session.mount('https://', PatchedHTTPAdapter())

        service = client.bind(wsdl['service'], wsdl['port'])
        operation = service[wsdl[operation]]

        return operation

    @api.model
    def _get_zeep_registration_operations(self):
        return self._get_zeep_operations('registration')

    @api.model
    def _send_batch(self, batch_dict):
        info = {
            'errors': [],
            'record_info': {},
        }
        errors = info['errors']
        record_info = info['record_info']

        try:
            register = self._get_zeep_registration_operations()
        except (zeep.exceptions.Error, requests.exceptions.RequestException) as error:
            errors.append(_("Networking error:\n%s", error))
            return info

        try:
            res = register(batch_dict['Cabecera'], batch_dict['RegistroFactura'])
            # `res` is of type 'zeep.client.SerialProxy'
        except requests.exceptions.SSLError:
            errors.append(_("The SSL certificate could not be validated."))
        except zeep.exceptions.TransportError as error:
            certificate_error = "No autorizado. Se ha producido un error al verificar el certificado presentado"
            if certificate_error in error.message:
                errors.append(_("The document could not be sent; the access was denied due to a problem with the certificate."))
            else:
                errors.append(_("Networking error while sending the document:\n%s", error))
        except requests.exceptions.RequestException as error:
            errors.append(_("Networking error while sending the document:\n%s", error))
        except zeep.exceptions.Fault as soapfault:
            info['state'] = 'rejected'
            errors.append(f"[{soapfault.code}] {soapfault.message}")
        except zeep.exceptions.Error as error:
            errors.append(_("Error while sending the batch document:\n%s", error))

        if errors:
            return info

        received_batch_state = res['EstadoEnvio']
        batch_state = {
            'Incorrecto': 'rejected',
            'ParcialmenteCorrecto': 'registered_with_errors',
            'Correcto': 'accepted',
        }[received_batch_state]

        info.update({
            'response_csv': res['CSV'] if 'CSV' in res else None,  # noqa: SIM401 - `res` is of type 'zeep.client.SerialProxy'
            'waiting_time_seconds': int(res['TiempoEsperaEnvio']),
            'state': batch_state,
        })

        for response_line in res['RespuestaLinea']:
            record_id = response_line['IDFactura']
            invoice_issuer = record_id['IDEmisorFactura'].strip()
            invoice_name = record_id['NumSerieFactura'].strip()
            record_key = str((invoice_issuer, invoice_name))

            operation_type = response_line['Operacion']['TipoOperacion']

            received_state = response_line['EstadoRegistro']
            state = {
                'Incorrecto': 'rejected',
                'AceptadoConErrores': 'registered_with_errors',
                'Correcto': 'accepted',
            }[received_state]

            errors = []
            if state in ('rejected', 'registered_with_errors'):
                error_code = response_line['CodigoErrorRegistro']
                error_description = response_line['DescripcionErrorRegistro']
                errors.append(f"[{error_code}] {error_description}")
            record_info[record_key] = {
                'state': state,
                'cancellation': operation_type == 'Anulacion',
                'errors': errors,
            }

        return info

    def _send_as_batch(self):
        # Documents in `self` should all belong to `self.env.company`.
        # For the cron we specifically set the `self.env.company` on some functions we call.
        sender_company = self.env.company

        batch_errors = self.with_company(sender_company)._send_as_batch_check()
        if batch_errors:
            error_title = _("The batch document could not be created")
            self.errors = self._format_errors(error_title, batch_errors)
            info = {'errors': batch_errors}
            return None, info

        # When the document is sent more than 240s after its creation the AEAT registers the document only with an error
        # See error with code 2004:
        #   El valor del campo FechaHoraHusoGenRegistro debe ser la fecha actual del sistema de la AEAT,
        #   admitiéndose un margen de error de: 240 segundos.
        incident = any(document.create_date > self.env.cr.now() + timedelta(seconds=240) for document in self)

        document_dict_list = [document._get_document_dict() for document in self]
        batch_dict = self.with_company(sender_company)._get_batch_dict(document_dict_list, incident=incident)

        info = self.with_company(sender_company)._send_batch(batch_dict)

        # Store the information from the response split over the individual documents
        for document in self:
            response_info = document._get_response_info(info)

            # The errors have to be formatted (as HTML) before storing them on the document
            errors_html = False
            error_list = response_info.get('errors', [])
            if error_list:
                error_title = _("Error")
                if response_info.get('state', False):
                    error_title = _("The Veri*Factu document contains the following errors according to the AEAT")
                errors_html = self._format_errors(error_title, error_list)
            document.errors = errors_html

            # All other values can be stored directly on the document
            keys = ['response_csv', 'state']
            for key in keys:
                new_value = response_info.get(key, False)
                if new_value or document[key]:
                    document[key] = new_value

            # To avoid losing data we commit after every document
            if self.env['account.move']._can_commit():
                self._cr.commit()

        waiting_time_seconds = info.get('waiting_time_seconds')
        if waiting_time_seconds:
            now = fields.Datetime.to_datetime(fields.Datetime.now())
            next_batch_time = now + timedelta(seconds=waiting_time_seconds)
            self.env.company.l10n_es_edi_verifactu_next_batch_time = next_batch_time

        self._post_send_hook(info)

        if self.env['account.move']._can_commit():
            self._cr.commit()

        return batch_dict, info

    @api.model
    def _send_as_batch_check(self):
        # The batching / sending may happen after the initial check
        errors = []
        company = self.env.company  # sending company

        company_values = company._l10n_es_edi_verifactu_get_values()
        company_NIF = company_values['NIF']
        if not company_NIF or len(company_NIF) != 9:  # NIFType
            errors.append(_("The NIF '%(company_NIF)s' of the company is not exactly 9 characters long.",
                            company_NIF=company_NIF))

        certificate = company.sudo()._l10n_es_edi_verifactu_get_certificate()
        if not certificate:
            errors.append(_("There is no certificate configured for Veri*Factu on the company."))

        return errors

    @api.model
    def _get_batch_dict(self, document_dict_list, incident=False):
        company = self.env.company
        company_values = company._l10n_es_edi_verifactu_get_values()

        batch_dict = {
          "Cabecera": {
              "ObligadoEmision": {
                  "NombreRazon": company_values['name'],
                  "NIF": company_values['NIF'],
              },
              "RemisionVoluntaria": {
                  "Incidencia": 'S' if incident else 'N',
              },
          },
            "RegistroFactura": document_dict_list,
        }

        return batch_dict

    def _get_response_info(self, info):
        # `info` is like returned from `_send_batch`
        self.ensure_one()

        record_key = self._get_record_key()
        batch_state = info.get('state')
        record_info = info.get('record_info', {})

        response_info = None
        if not batch_state and info['errors']:
            # Handle case that something went wrong while sending or parsing the respone
            response_info = {'errors': info['errors']}
        elif record_info:
            # We expect an entry for `record_identifier`.
            # If there is none we "build" one; it indicates a parsing failure.
            response_info = record_info.get(record_key, None)
            if response_info is None:
                response_info = {
                    'errors': [_("We could not find any information about the record in the linked batch document.")],
                }
        else:
            # I.e. in case of soapfault and access denied there is no `record_info`.
            # So we just return the global 'state' / 'errors'.
            response_info = {
                'state': info['state'],
                'errors': info['errors'],
            }

        # Add some information from the batch level in any case.
        response_info.update({
            'waiting_time_seconds': info.get('waiting_time_seconds', False),
            'response_csv': info.get('response_csv', False),
        })

        return response_info

    def _get_record_key(self):
        self.ensure_one()
        record_identifier = self.record_identifier
        return str((record_identifier['IDEmisorFactura'], record_identifier['NumSerieFactura']))

    def _post_send_hook(self, info):
        # This function should not raise since it may be called "in the middle" of the sending process
        for document in self:
            invoice = document.move_id
            if invoice.l10n_es_edi_verifactu_state == 'cancelled' and invoice.state != 'cancel':
                with contextlib.suppress(UserError):
                    invoice.button_cancel()

    @api.ondelete(at_uninstall=False)
    def _never_unlink_chained_documents(self):
        for document in self:
            if document.chain_index:
                raise UserError(_("You cannot delete Veri*Factu Documents that are part of the chain of all Veri*Factu Documents."))

    @api.model
    def _format_date_fecha_type(self, date):
        # Format as 'fecha' type from xsd
        return date.strftime('%d-%m-%Y')

    @api.model
    def _round_format_number_2(self, number):
        # Round and format as number with 2 precision digits
        if number is None:
            return None
        rounded = float_round(number, precision_digits=2)
        return float_repr(rounded, precision_digits=2)

    # We do not check / fix the number of digits in front of the decimal separator
    _format_number_ImporteSgn12_2 = _round_format_number_2
    _format_number_Tipo2_2 = _round_format_number_2

    @api.model
    def _render_vals(self, vals, previous_record_identifier=None):
        def remove_None_and_False(value):
            # Remove `None` and `False` from dictionaries
            if isinstance(value, dict):
                return {
                    key: remove_None_and_False(value)
                    for key, value in value.items()
                    if value is not None and value is not False
                }
            elif isinstance(value, list):
                return [remove_None_and_False(v) for v in value]
            else:
                return value

        cancellation = vals['cancellation']
        company = vals['company']
        record_type = 'RegistroAnulacion' if cancellation else 'RegistroAlta'
        render_vals = {
            'company': company,
            'record_type': record_type,
            'record': vals['record'],
            'cancellation': cancellation,
            'vals': vals,
            'previous_record_identifier': previous_record_identifier,
        }

        generation_time_string = fields.Datetime.now(timezone('Europe/Madrid')).astimezone(timezone('Europe/Madrid')).isoformat()

        record_type_vals = {}
        record_type_vals.update({
            'IDVersion': VERIFACTU_VERSION,
            'FechaHoraHusoGenRegistro': generation_time_string,
        })

        render_vals_functions = [
            self._render_vals_operation,
            self._render_vals_previous_submissions,
            self._render_vals_monetary_amounts,
            self._render_vals_SistemaInformatico,
        ]
        for function in render_vals_functions:
            new_render_vals = function(vals)
            record_type_vals.update(new_render_vals)

        render_vals[record_type] = remove_None_and_False(record_type_vals)

        self._update_render_vals_with_chaining_info(render_vals)

        record_identifier = self._extract_record_identifiers(render_vals)
        render_vals['record_identifier'] = record_identifier

        return render_vals

    @api.model
    def _render_vals_operation(self, vals):
        company = vals['company']
        cancellation = vals['cancellation']
        invoice_date = self._format_date_fecha_type(vals['invoice_date'])
        is_simplified = vals['is_simplified']
        move_type = vals['move_type']
        name = vals['name']
        partner = vals['partner']

        company_values = company._l10n_es_edi_verifactu_get_values()
        company_NIF = company_values['NIF']
        company_name = company_values['name']

        if cancellation:
            render_vals = {
                'IDFactura': {
                    'IDEmisorFacturaAnulada': company_NIF,
                    'NumSerieFacturaAnulada': name,
                    'FechaExpedicionFacturaAnulada': invoice_date,
                }
            }
            return render_vals

        render_vals = {
            'NombreRazonEmisor': company_name,
            'IDFactura': {
                'IDEmisorFactura': company_NIF,
                'NumSerieFactura': name,
                'FechaExpedicionFactura': invoice_date,
            }
        }

        simplified_partner = self.env.ref('l10n_es.partner_simplified', raise_if_not_found=False)
        partner_is_simplified_partner = simplified_partner and partner == simplified_partner
        partner_specified = partner and not partner_is_simplified_partner

        # TODO: we could face zeep xsd validation issue here too
        if partner and not partner_is_simplified_partner:
            render_vals['Destinatarios'] = {
                'IDDestinatario': [{
                    'NombreRazon': (partner.name or '')[:120],
                    ** partner._l10n_es_edi_get_partner_info(),
                }]
            }

        delivery_date = vals['delivery_date']
        if delivery_date:
            delivery_date = self._format_date_fecha_type(delivery_date)

        if move_type == 'out_invoice':
            tipo_factura = 'F2' if is_simplified and not partner_specified else 'F1'
            tipo_rectificativa = None
        else:
            # move_type == 'out_refund':
            tipo_factura = 'R5' if is_simplified else 'R1'
            tipo_rectificativa = 'I'

        render_vals.update({
            'TipoFactura': tipo_factura,
            'TipoRectificativa': tipo_rectificativa,  # may be None
            'FechaOperacion': delivery_date if delivery_date and delivery_date != invoice_date else None,
            'DescripcionOperacion': vals['description'] or 'manual',
            # Note: error [1183]
            # El campo FacturaSimplificadaArticulos7273 solo se podrá rellenar con S
            # si TipoFactura es de tipo F1 o F3 o R1 o R2 o R3 o R4.
            'FacturaSimplificadaArt7273': 'S' if is_simplified and partner_specified else None,
            'FacturaSinIdentifDestinatarioArt61d': 'S' if is_simplified and not partner_specified else None,
        })

        refunded_document = vals['refunded_document']
        if refunded_document:
            refunded_record_identifier = refunded_document.record_identifier
            render_vals.update({
                'FacturasRectificadas': [{
                    'IDFacturaRectificada': {
                        'IDEmisorFactura': refunded_record_identifier['IDEmisorFactura'],
                        'NumSerieFactura': refunded_record_identifier['NumSerieFactura'],
                        'FechaExpedicionFactura': refunded_record_identifier['FechaExpedicionFactura'],
                    }
                }],
            })

        return render_vals

    @api.model
    def _render_vals_previous_submissions(self, vals):
        # See "Sistemas Informáticos de Facturación y Sistemas VERI*FACTU" Version 1.0.0 - "Validaciones" p. 22 f.
        render_vals = {}

        # Note: We do not allow generating documents that would change the record identifier (i.e. the keys in the QR code)
        verifactu_state = vals['verifactu_state']
        submission_rejected_before = vals['rejected_before']
        verifactu_registered_with_document = verifactu_state in ('registered_with_errors', 'accepted')
        # In some cases we may not have the document / response which led to the registration
        verifactu_registered_without_document = bool(
            # We may not know it is registered due to a timeout (we sent it but did not get / process the response).
            # But then we will get a duplicate error when re-sending the document.
            vals['documents'].filtered(
            lambda doc: (doc.document_type == 'submission'
                         and doc.state == 'rejected'
                         and doc.errors
                         and "[3000] Registro de facturación duplicado." in doc.errors))
        )
        verifactu_registered = verifactu_registered_with_document or verifactu_registered_without_document
        # The record may be otherwise known to the AEAT;
        # i.e. when switching to Veri*Factu after the original invoice was created.
        # TODO: Currently not implemented / can not happen
        otherwise_known_to_AEAT = not verifactu_registered and vals['record_identifier']

        if vals['cancellation']:
            render_vals = {
                # A cancelled record can e.g. not exist at the AEAT when we switch to Veri*Factu after the original invoice was created
                'SinRegistroPrevio': 'S' if not verifactu_registered else 'N',
                'RechazoPrevio': 'S' if submission_rejected_before else 'N',
            }
        else:
            substitution = verifactu_registered or otherwise_known_to_AEAT
            if substitution and not verifactu_registered:
                # Cases: ALTA DE SUBSANACIÓN SIN REGISTRO PREVIO, ALTA POR RECHAZO DE SUBSANACIÓN SIN REGISTRO PREVIO
                # TODO: This case can only happen after `otherwise_known_to_AEAT` is implemented
                previously_rejected_state = 'X'
            elif submission_rejected_before:
                # Cases: ALTA POR RECHAZO, ALTA POR RECHAZO DE SUBSANACIÓN
                previously_rejected_state = 'S' if substitution else 'X'
            else:
                # Cases: ALTA, ALTA DE SUBSANACIÓN
                previously_rejected_state = None  # 'N'
            render_vals = {
                # We only put 'N' for 'Subsanacion' in case ALTA (we also put 'S' in case ALTA POR RECHAZO)
                'Subsanacion': 'S' if substitution or submission_rejected_before else 'N',
                'RechazoPrevio': previously_rejected_state,
            }

        return render_vals

    @api.model
    def _render_vals_monetary_amounts(self, vals):
        if vals['cancellation']:
            return {}
        # We only support a single verifactu tax type / clave regimen per record.
        # For moves these values are selected via `l10n_es_edi_verifactu_operation_type`.
        verifactu_tax_type = vals['verifactu_tax_type']
        clave_regimen = vals['clave_regimen']

        sujeto_tax_types = self.env['account.tax']._l10n_es_get_sujeto_tax_types()

        detalles = []
        tax_details = vals['tax_details']

        recargo_tax_details_key = {}  # dict (tax_key -> recargo_tax_key)
        for tax_details_per_record in tax_details['tax_details_per_record'].values():
            record_tax_details = tax_details_per_record['tax_details']
            main_key = None
            recargo_key = None
            # Note: There is only a single (main tax, recargo tax) pair on a single invoice line
            #       (if any; see `_check_record_values`)
            for key in record_tax_details:
                if key['recargo_taxes']:
                    main_key = key
                if key['l10n_es_type'] == 'recargo':
                    recargo_key = key
                if main_key and recargo_key:
                    break
            recargo_tax_details_key[main_key] = recargo_key

        sign = -1 if vals['move_type'] in ('out_refund', 'in_refund') else 1
        for key, tax_detail in tax_details['tax_details'].items():
            tax_type = tax_detail['l10n_es_type']
            # Tax types 'ignore' and 'retencion' are ignored when generating the `tax_details`
            # See `filter_to_apply` in function `_l10n_es_edi_verifactu_get_tax_details_functions` on 'account.tax'
            if tax_type == 'recargo':
                # Recargo taxes are only used in combination with another tax (a sujeto tax)
                # They will be handled when processing the remaining taxes
                continue

            exempt_reason = tax_detail['l10n_es_exempt_reason']  # only set if exempt

            tax_percentage = tax_detail['amount']
            base_amount = sign * tax_detail['base_amount']
            tax_amount = math.copysign(tax_detail['tax_amount'], base_amount)

            calificacion_operacion = None  # Reported if not tax-exempt;
            recargo_equivalencia = {}
            if tax_type in sujeto_tax_types:
                calificacion_operacion = 'S2' if tax_type == 'sujeto_isp' else 'S1'
                if tax_detail['recargo_taxes']:
                    recargo_key = recargo_tax_details_key.get(key)
                    recargo_tax_detail = tax_details['tax_details'][recargo_key]
                    recargo_tax_percentage = recargo_tax_detail['amount']
                    recargo_tax_amount = math.copysign(recargo_tax_detail['tax_amount'], base_amount)
                    recargo_equivalencia.update({
                        'tax_percentage': recargo_tax_percentage,
                        'tax_amount': recargo_tax_amount,
                    })
            elif tax_type in ('no_sujeto', 'no_sujeto_loc'):
                calificacion_operacion = 'N2' if tax_type == 'no_sujeto_loc' else 'N1'
            else:
                # tax_type == 'exento' (see `_check_record_values`)
                # exempt_reason set already
                # [1238]
                #     Si la operacion es exenta no se puede informar ninguno de los campos
                #     TipoImpositivo, CuotaRepercutida, TipoRecargoEquivalencia y CuotaRecargoEquivalencia.
                tax_percentage = None
                tax_amount = None
                recargo_percentage = None
                recargo_amount = None

            recargo_percentage = recargo_equivalencia.get('tax_percentage')
            recargo_amount = recargo_equivalencia.get('tax_amount')

            # Note on the TipoImpositivo and CuotaRepercutida tags.
            # In some cases it makes a difference for the validation whether the tags are output with 0
            # or not at all:
            # - In the no sujeto cases (calification_operacion in ('N1', 'N2')) we may not include them.
            # - In the (calification_operacion == S2) case the tags have to be included with value 0.
            #
            # See the following errors
            # [1198]
            #     Si CalificacionOperacion es S2 TipoImpositivo y CuotaRepercutida deberan tener valor 0.
            if calificacion_operacion in ('N1', 'N2') and verifactu_tax_type == '01':
                tax_percentage = None
                tax_amount = None

            detalle = {
                'Impuesto': verifactu_tax_type,
                'ClaveRegimen': clave_regimen,
                'CalificacionOperacion': calificacion_operacion,
                'OperacionExenta': exempt_reason,
                'TipoImpositivo': self._format_number_Tipo2_2(tax_percentage),
                'BaseImponibleOimporteNoSujeto': self._format_number_ImporteSgn12_2(base_amount),
                'CuotaRepercutida': self._format_number_ImporteSgn12_2(tax_amount),
                'TipoRecargoEquivalencia': self._format_number_Tipo2_2(recargo_percentage),
                'CuotaRecargoEquivalencia': self._format_number_ImporteSgn12_2(recargo_amount),
            }

            detalles.append(detalle)

        total_amount = sign * (tax_details['base_amount'] + tax_details['tax_amount'])
        tax_amount = sign * (tax_details['tax_amount'])

        render_vals = {
            'Macrodato': 'S' if abs(total_amount) >= 100000000 else None,
            'Desglose': {
                'DetalleDesglose': detalles
            },
            'CuotaTotal': self._format_number_ImporteSgn12_2(tax_amount),
            'ImporteTotal': self._format_number_ImporteSgn12_2(total_amount),
        }

        return render_vals

    @api.model
    def _get_db_identifier(self):
        database_uuid = self.env['ir.config_parameter'].sudo().get_param('database.uuid')
        return _sha256(database_uuid)

    @api.model
    def _render_vals_SistemaInformatico(self, vals):
        spanish_companies_on_db_count = self.env['res.company'].search_count([
            ('account_fiscal_country_id.code', '=', 'ES'),
        ], limit=2)

        render_vals = {
            'SistemaInformatico': {
                'NombreRazon': 'ODOO ERP SP SL',
                'NIF': 'B72659014',
                'NombreSistemaInformatico': odoo.release.product_name,
                'IdSistemaInformatico': '00',  # identifies Odoo the software as product of Odoo the company
                'Version': odoo.release.version,
                'NumeroInstalacion':  self._get_db_identifier(),
                'TipoUsoPosibleSoloVerifactu': 'S',
                'TipoUsoPosibleMultiOT': 'S',
                'IndicadorMultiplesOT': 'S' if spanish_companies_on_db_count > 1 else 'N',
            },
        }

        return render_vals

    def _extract_record_identifiers(self, render_vals):
        """Return a dictionary that includes:
          * the IDFactura fields
          * the fields used for the fingerprint generation of this document and the next one
            (The fingerprint of this record is part of the fingerprint generation of the next record)
          * the fields used for QR code generation
        """
        record_type_vals = render_vals[render_vals['record_type']]
        identifiers = {
            'FechaHoraHusoGenRegistro': record_type_vals['FechaHoraHusoGenRegistro'],
            'Huella': record_type_vals['Huella'],
        }
        id_factura = record_type_vals['IDFactura']
        if render_vals['cancellation']:
            identifiers.update({
                'IDEmisorFactura': id_factura['IDEmisorFacturaAnulada'],
                'NumSerieFactura': id_factura['NumSerieFacturaAnulada'],
                'FechaExpedicionFactura': id_factura['FechaExpedicionFacturaAnulada'],
            })
        else:
            identifiers.update({
                'IDEmisorFactura': id_factura['IDEmisorFactura'],
                'NumSerieFactura': id_factura['NumSerieFactura'],
                'FechaExpedicionFactura': id_factura['FechaExpedicionFactura'],
                'TipoFactura': record_type_vals['TipoFactura'],
                'CuotaTotal': record_type_vals['CuotaTotal'],
                'ImporteTotal': record_type_vals['ImporteTotal'],
            })
        return identifiers

    @api.model
    def _update_render_vals_with_chaining_info(self, render_vals):
        record_type_vals = render_vals[render_vals['record_type']]
        predecessor = (render_vals['previous_record_identifier'] or {})
        first_registration = not bool(predecessor)

        if first_registration:
            encadenamiento = {
                'PrimerRegistro': 'S',
            }
        else:
            encadenamiento = {
                'RegistroAnterior': {
                    'IDEmisorFactura': predecessor.get('IDEmisorFactura'),
                    'NumSerieFactura': predecessor.get('NumSerieFactura'),
                    'FechaExpedicionFactura': predecessor.get('FechaExpedicionFactura'),
                    'Huella': predecessor.get('Huella'),
                }
            }
        # The 'Encadenamiento' info needs to be set already during the `_fingerprint` computation
        record_type_vals['Encadenamiento'] = encadenamiento

        record_type_vals.update({
            'TipoHuella': "01",  # "01" means SHA-256
            'Huella': self._fingerprint(render_vals),
        })

        return render_vals

    @api.model
    def _fingerprint(self, render_vals):
        """
        Documentation: "Detalle de las especificaciones técnicas para generación de la huella o hash de los registros de facturación"
        """
        record_type_vals = render_vals[render_vals['record_type']]
        id_factura = record_type_vals['IDFactura']
        registro_anterior = record_type_vals['Encadenamiento'].get('RegistroAnterior')  # does not exist for the first document
        if render_vals['cancellation']:
            fingerprint_values = [
                ('IDEmisorFacturaAnulada', id_factura['IDEmisorFacturaAnulada']),
                ('NumSerieFacturaAnulada', id_factura['NumSerieFacturaAnulada']),
                ('FechaExpedicionFacturaAnulada', id_factura['FechaExpedicionFacturaAnulada']),
                ('Huella', registro_anterior['Huella'] if registro_anterior else ''),
                ('FechaHoraHusoGenRegistro', record_type_vals['FechaHoraHusoGenRegistro']),
            ]
            string = "&".join([f"{field}={value.strip()}" for (field, value) in fingerprint_values])
        else:
            fingerprint_values = [
                ('IDEmisorFactura', id_factura['IDEmisorFactura']),
                ('NumSerieFactura', id_factura['NumSerieFactura']),
                ('FechaExpedicionFactura', id_factura['FechaExpedicionFactura']),
                ('TipoFactura', record_type_vals['TipoFactura']),
                ('CuotaTotal', record_type_vals['CuotaTotal']),
                ('ImporteTotal', record_type_vals['ImporteTotal']),
                ('Huella', registro_anterior['Huella'] if registro_anterior else ''),
                ('FechaHoraHusoGenRegistro', record_type_vals['FechaHoraHusoGenRegistro']),
            ]
            string = "&".join([f"{field}={value.strip()}" for (field, value) in fingerprint_values])
        return _sha256(string)

    def _filter_waiting(self):
        return self.filtered(lambda doc: not doc.state and doc.json_attachment_id)

    def _get_last(self, document_type):
        return self.filtered(lambda doc: doc.document_type == document_type and doc.json_attachment_id).sorted()[:1]

    def _get_state(self):
        last_registered_document = self.filtered(lambda doc: doc.state in ('registered_with_errors', 'accepted')).sorted()[:1]
        if last_registered_document:
            cancellation = last_registered_document.document_type == 'cancellation'
            return 'cancelled' if cancellation else last_registered_document.state

        rejected_document = self.filtered(lambda doc: doc.state == 'rejected')[:1]
        if rejected_document:
            return 'rejected'

        return False

    def _get_qr_code_img_url(self):
        self.ensure_one()
        record_identifier = self.record_identifier
        if not record_identifier or self.document_type != 'submission':
            # We take the values from the record identifier.
            # And only the 'submission' has all the necessary values ('ImporteTotal').
            return False
        endpoint_url = self.company_id._l10n_es_edi_verifactu_get_endpoints()['QR']
        url_params = url_encode({
            'nif': record_identifier['IDEmisorFactura'],
            'numserie': record_identifier['NumSerieFactura'],
            'fecha': record_identifier['FechaExpedicionFactura'],
            'importe': record_identifier['ImporteTotal'],
        })
        url = url_quote_plus(f"{endpoint_url}?{url_params}")
        return f'/report/barcode/?barcode_type=QR&value={url}&barLevel=M&width=180&height=180'
