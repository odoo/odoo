from dateutil.relativedelta import relativedelta
from lxml import etree

import requests.exceptions

from odoo import _, api, fields, models
from odoo.addons.l10n_es.models.http_adapter import PatchedHTTPAdapter
from odoo.exceptions import UserError


BATCH_LIMIT = 1000

# We store the errors as a language-independent code to avoid storing translated strings
# Document Errors
ERROR_NOTHING_TO_SEND = 'nothing_to_send'
ERROR_UNSUPPORTED_REQUEST_TYPE = 'unsupported_request_type'
ERROR_REQUEST_FAILED = 'request_failed'
ERROR_SOAPFAULT = 'soapfault'
# Parse Errors
ERROR_UNSUPPORTED_CONTENT_TYPE = 'unsupported_content_type'
ERROR_MALFORMED_RESPONSE = 'malformed_response'
ERROR_MALFORMED_RESPONSE_STATE = 'malformed_response_state'
# "Normal" Errors
ERROR_ACCESS_DENIED = 'access_denied'
ERROR_MALFORMED_DOCUMENT = 'malformed_document'


class L10nEsEdiVerifactuRequest(models.Model):
    """Veri*Factu Request
    It represents a Veri*Factu request to the AEAT (and eventually information about the received response).
    It i.e. handles the requests we send to the AEAT.
      * stores the request we send (XML)
        * A Batch Request basically just aggregates one or several "Veri*Factu Documents" ('l10n_es_edi_verifactu.document').
      * and stores information about the received response
    Also see the docstring of the "Veri*Factu Record Mixin" for more details about the general flow.
    """
    _name = 'l10n_es_edi_verifactu.request'
    _description = "Veri*Factu Request"
    _order = 'create_date DESC, id DESC'

    company_id = fields.Many2one(
        comodel_name='res.company',
        default=lambda self: self.env.company,
        required=True,
        readonly=True,
    )
    request_type = fields.Selection(
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
    response_info = fields.Json(
        string="Response Info",
        readonly=True,
        copy=False,
        help="Technical Field providing information extracted from the response from the AEAT.",
    )
    response_message = fields.Text(
        copy=False,
        readonly=True,
        store=True,
    )

    @api.ondelete(at_uninstall=False)
    def _never_unlink_documents(self):
        if self.request_type == 'batch':
            raise UserError(_("You cannot delete information about succesfully sent Veri*Factu batches."))

    @api.depends('request_type')
    def _compute_display_name(self):
        for document in self:
            document.display_name = document._get_attachment_filename()

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
        request_type = 'consulta' if self.request_type == 'query' else 'remision'
        return f"verifactu_{self.id}_{request_type}.xml"

    @api.model
    def _get_record_key(self, record_identifier):
        # `record_identifier` is a dictionary like belonging to `'record_identifier'` in render values
        return str((record_identifier['IDEmisorFactura'], record_identifier['NumSerieFactura']))

    @api.model
    def _translate_error_tuple(self, error_tuple):
        error_type, error_message = error_tuple

        type_string = {
            ERROR_NOTHING_TO_SEND: _("There is no XML attachment to send."),
            ERROR_UNSUPPORTED_REQUEST_TYPE: _("The request type is currently not supported"),
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

        record_key = self._get_record_key(record_identifier)
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
    def _send_batch(self, documents):
        # `documents` all belong to `self.env.company`

        # TODO: incident: yes if we one of the documents is older than 120 secs

        # For the cron we specifically set the `self.env.company`
        batch_xml, batch_errors = documents.with_company(self.env.company)._create_batch_xml()
        if batch_errors:
            return None, {'errors': batch_errors}

        info = self._send(batch_xml, 'batch')
        if info['errors']:
            return None, info

        request = self.create({
            'request_type': 'batch',
            'response_info': info,
            'response_message': info['response_message'],
        })
        request._add_attachment_from_xml(batch_xml)
        documents.request_id = request

        if self.env['account.move']._can_commit():
            self._cr.commit()

        return request, info

    @api.model
    def _get_time_for_next_batch(self, company):
        # TODO: put a field on the company
        Document = self.env['l10n_es_edi_verifactu.document']
        last_document = Document.sudo().search([
            ('company_id', '=', company.id),
            ('response_time', '!=', False),
            ('request_id.response_info', '!=', False),
        ], order=Document._order, limit=1)
        if last_document:
            # In case of rejection due to soap fault we get no waiting_time_seconds.
            # 60 seconds is the default value mentioned in the documentation
            seconds_to_wait = last_document.request_id.response_info.get('waiting_time_seconds') or 60
            return last_document.response_time + relativedelta(seconds=seconds_to_wait)
        return False

    @api.model
    def trigger_next_batch(self):
        """
        1. Send all waiting documents that we can send.
        2. Trigger the cron again at a later date to send the documents we could not send
        """
        documents_per_company = self.env['l10n_es_edi_verifactu.document']._read_group(
            [('request_id', '=', False)],
            groupby=['company_id'],
            aggregates=['id:recordset'],
        )

        if not documents_per_company:
            return

        for company, documents in documents_per_company:
            # We sort the `documents` to batch them in the order they were chained (`create_date`).
            # TODO: explicitly sorting by `create_date` may be better
            documents = documents.sorted(reverse=True)

            # Send batches with size BATCH_LIMIT; they are not restricted by the waiting time
            next_batch = documents[0:BATCH_LIMIT]
            start_index = 0
            while len(next_batch) == BATCH_LIMIT:
                self.with_company(company)._send_batch(next_batch)
                start_index += BATCH_LIMIT
                next_batch = documents[start_index:start_index + BATCH_LIMIT]
            # now: len(next_batch) < BATCH_LIMIT ; we need to respect the waiting time

            if not next_batch:
                continue

            next_batch_time = self._get_time_for_next_batch(company)
            if not next_batch_time or fields.Datetime.now() >= next_batch_time:
                self.with_company(company)._send_batch(next_batch)
            else:
                cron = self.env.ref('l10n_es_edi_verifactu.cron_verifactu_batch', raise_if_not_found=False)
                if cron:
                    cron._trigger(at=next_batch_time)

    @api.model
    def _soap_request(self, xml):
        company = self.env.company

        session = requests.Session()
        session.cert = company.sudo()._l10n_es_edi_verifactu_get_certificate()
        session.mount("https://", PatchedHTTPAdapter())

        soap_xml = self.env['l10n_es_edi_verifactu.xml']._build_soap_request_xml(xml)

        response = session.request(
            'post',
            url=company._l10n_es_edi_verifactu_get_endpoints()['verifactu'],
            data=soap_xml,
            timeout=15,
            headers={"Content-Type": 'application/soap+xml;charset=UTF-8'},
        )

        return response

    @api.model
    def _send(self, xml, request_type):
        company = self.env.company

        info = {
            'errors': [],
            'response': None,
            'response_message': False,
            'response_time': False,
        }

        if request_type not in ('batch', 'query'):
            info['errors'].append((ERROR_UNSUPPORTED_REQUEST_TYPE, None))
            info['state'] = 'sending_failed'
            return info

        try:
            response = self._soap_request(xml)
            info['response'] = response
            info['response_message'] = response.text
        except requests.exceptions.RequestException as e:
            info['errors'].append((ERROR_REQUEST_FAILED, f"{e}"))
            info['state'] = 'sending_failed'
        info['response_time'] = fields.Datetime.to_string(fields.Datetime.now())

        response = info['response']
        if response:
            parse_info = self._parse_response(response, request_type=request_type)
            info['errors'].extend(parse_info.pop('errors', []))
            info.update(parse_info)

        if 'state' not in info:
            info['errors'].append((ERROR_MALFORMED_RESPONSE_STATE, None))
            info['state'] = 'parsing_failed'

        # remove non-serializable values
        info.pop('xml_tree', None)
        info.pop('html_tree', None)
        info.pop('response', None)
        return info

    @api.model
    def _parse_response(self, response, request_type):
        errors = []
        info = {
            'errors': errors,  # List of (internal_error_type, error_message_from_response)
            'request_type': request_type,
            'record_info': {},
        }

        self._parse_response_content_type(response, info)
        if info['content_type'] == 'HTML':
            self._parse_html_response(response, info)
        elif info['content_type'] == 'XML':
            self._parse_xml_response(response, info)
        else:
            errors.append((ERROR_UNSUPPORTED_CONTENT_TYPE, None))

        return info

    @api.model
    def _parse_response_content_type(self, response, info):
        if 'content-type' in response.headers:
            header = response.headers['content-type'].casefold()
            if header.startswith('text/xml'):
                info['content_type'] = 'XML'
            elif header.startswith('text/html'):
                info['content_type'] = 'HTML'

    @api.model
    def _parse_html_response(self, response, info):
        # Since it is a SOAP flow we should only get an HTML response in case of an access error
        # (and get an XML response otherwise)
        html_parser = etree.HTMLParser()
        info['html_tree'] = etree.fromstring(response.text, html_parser)
        self._parse_access_error_response(response, info)
        if not info['errors']:
            info['errors'].append((ERROR_ACCESS_DENIED, None))

    @api.model
    def _parse_access_error_response(self, response, info):
        html_tree = info['html_tree']
        main_node = html_tree.find(".//main")
        main_node_html = etree.tostring(main_node, pretty_print=True, method="html").decode()
        info['errors'].append((ERROR_ACCESS_DENIED, main_node_html))
        info['state'] = 'rejected'
        return info

    @api.model
    def _parse_xml_response(self, response, info):
        namespaces = {
            'env': "http://schemas.xmlsoap.org/soap/envelope/",
            'tikR': "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd",
            'tik': "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroInformacion.xsd",
            'tikLRRC': "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaConsultaLR.xsd",
        }
        info.update({
            'xml_tree': etree.fromstring(response.text.encode()),
            'namespaces': namespaces,
        })

        self._parse_response_for_soapfault(response, info)
        if info['errors']:
            return

        request_type = info['request_type']
        if request_type == 'batch':
            self._parse_batch_response(response, info)
        elif request_type == 'query':
            self._parse_query_response(response, info)
        else:
            info['errors'].append((ERROR_UNSUPPORTED_REQUEST_TYPE, None))

    @api.model
    def _parse_response_for_soapfault(self, response, info):
        errors = info['errors']
        xml_tree = info['xml_tree']
        namespaces = info['namespaces']

        soapfault_node = xml_tree.find(".//env:Fault", namespaces=namespaces)
        if soapfault_node is not None:
            info['state'] = 'rejected'
            faultcode_node = soapfault_node.find(".//faultcode", namespaces=namespaces)
            faultstring_node = soapfault_node.find(".//faultstring", namespaces=namespaces)
            error_message = None
            if faultcode_node is not None and faultstring_node is not None:
                error_message = f"[{faultcode_node.text}] {faultstring_node.text}"
            elif faultstring_node is not None:
                error_message = faultstring_node.text
            errors.append((ERROR_SOAPFAULT, error_message))

    @api.model
    def _parse_batch_response(self, response, info):
        errors = info['errors']
        xml_tree = info['xml_tree']
        namespaces = info['namespaces']
        record_info = info['record_info']

        registration_node = xml_tree.find("env:Body/tikR:RespuestaRegFactuSistemaFacturacion", namespaces=namespaces)
        if registration_node is None:
            errors.append((ERROR_MALFORMED_RESPONSE, None))
            return

        waiting_time_node = registration_node.find("tikR:TiempoEsperaEnvio", namespaces=namespaces)
        try:
            info['waiting_time_seconds'] = int(waiting_time_node.text)
        except ValueError:
            errors.append((ERROR_MALFORMED_RESPONSE, None))  # Should not happen

        batch_status_node = registration_node.find("tikR:EstadoEnvio", namespaces=namespaces)
        if batch_status_node is not None:
            batch_state_string = batch_status_node.text.strip()
            batch_state = {
                'Incorrecto': 'rejected',
                'ParcialmenteCorrecto': 'registered_with_errors',
                'Correcto': 'accepted',
               }.get(batch_state_string)
            if batch_state is None:
                # as of writing all possible values are implemented for EstadoEnvio
                errors.append((ERROR_MALFORMED_RESPONSE, None))
        info['state'] = batch_state or False

        identification_errors = []
        for element in registration_node.iterfind("tikR:RespuestaLinea", namespaces=namespaces):
            subdoc_errors = []

            # Determine an identifier (`record_key`) for the response line.
            # Sync with function `_get_record_key`
            invoice_id_node = element.find("tikR:IDFactura", namespaces=namespaces)
            if invoice_id_node is None:
                identification_errors.append((ERROR_MALFORMED_RESPONSE, None))
                continue
            issuer_id_node = invoice_id_node.find("tik:IDEmisorFactura", namespaces=namespaces)
            invoice_number_node = invoice_id_node.find("tik:NumSerieFactura", namespaces=namespaces)
            if issuer_id_node is None or invoice_number_node is None:
                identification_errors.append((ERROR_MALFORMED_RESPONSE, None))
                continue
            issuer = issuer_id_node.text.strip()
            invoice_name = invoice_number_node.text.strip()
            record_key = str((issuer, invoice_name))

            status_node = element.find("tikR:EstadoRegistro", namespaces=namespaces)
            if status_node is None:
                subdoc_errors.append((ERROR_MALFORMED_RESPONSE, None))
            status = status_node.text.strip()
            subdoc_state = {
                'Incorrecto': 'rejected',
                'AceptadoConErrores': 'registered_with_errors',
                'Correcto': 'accepted',
            }.get(status)
            if subdoc_state is None:
                # as of writing all possible values are implemented for EstadoRegistro
                subdoc_errors.append((ERROR_MALFORMED_RESPONSE, None))
                subdoc_state = False
            elif subdoc_state in ('rejected', 'registered_with_errors'):
                code_node = element.find("tikR:CodigoErrorRegistro", namespaces=namespaces)
                description_node = element.find("tikR:DescripcionErrorRegistro", namespaces=namespaces)
                if code_node is None or description_node is None:
                    subdoc_errors.append((ERROR_MALFORMED_RESPONSE, None))
                code = code_node.text.strip()
                description = description_node.text.strip()
                subdoc_errors.append((ERROR_MALFORMED_DOCUMENT, f"[{code}] {description}"))

            operation_type_node = element.find("tikR:Operacion/tik:TipoOperacion", namespaces=namespaces)
            operation_type = operation_type_node is not None and operation_type_node.text.strip()
            if not operation_type or operation_type not in ('Alta', 'Anulacion'):
                # as of writing all possible values are implemented
                subdoc_errors.append((ERROR_MALFORMED_RESPONSE, None))

            record_info[record_key]  = {
                'state': subdoc_state,
                'cancellation': operation_type == 'Anulacion',
                'errors': subdoc_errors,
            }
        if identification_errors:
            record_info[None] = {'errors': identification_errors}

    @api.model
    def _parse_query_response(self, response, info):
        errors = info['errors']
        xml_tree = info['xml_tree']
        namespaces = info['namespaces']

        query_node = xml_tree.find("env:Body/tikLRRC:RespuestaConsultaFactuSistemaFacturacion", namespaces=namespaces)
        if query_node is None:
            errors.append((ERROR_MALFORMED_RESPONSE, None))
            return

        raise NotImplementedError
