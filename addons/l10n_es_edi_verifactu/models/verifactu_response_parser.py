from lxml import etree

from odoo import _, api, models

# Parse Errors
ERROR_UNSUPPORTED_CONTENT_TYPE = 'unsupported_content_type'
ERROR_UNSUPPORTED_DOCUMENT_TYPE = 'unsupported_document_type'
ERROR_MALFORMED_RESPONSE = 'malformed_response'
# "Normal" Errors
ERROR_ACCESS_DENIED = 'access_denied'
ERROR_SOAPFAULT = 'soapfault'
ERROR_MALFORMED_DOCUMENT = 'malformed_document'


class L10nEsEdiVerifactuResponseParser(models.AbstractModel):
    """ Handles the parsing of the response from the AEAT after submitting a request to them. """
    _name = 'l10n_es_edi_verifactu.response_parser'
    _description = "Veri*Factu Response Parser"

    @api.model
    def _translate_error_tuple(self, error_tuple):
        error_type, error_message = error_tuple

        type_string = {
            ERROR_UNSUPPORTED_CONTENT_TYPE: _("We can not parse documents with that content type"),
            ERROR_UNSUPPORTED_DOCUMENT_TYPE: _("The document type is currently not supported"),
            ERROR_MALFORMED_RESPONSE: _("The response could not be parsed"),
            ERROR_ACCESS_DENIED: _("The document could not be sent; the access was denied"),
            ERROR_SOAPFAULT: _("The document was rejected by the AEAT"),
        }

        if error_type == ERROR_MALFORMED_DOCUMENT or error_type not in type_string:
            return error_message or _("Unknown error.")

        error_type_string = type_string[error_type]

        if error_message:
            return f"{error_type_string}: {error_message}"

        return error_type_string

    @api.model
    def _parse_response(self, response, document_type):
        errors = []
        info = {
            'errors': errors,  # List of (internal_error_type, error_message_from_response)
            'document_type': document_type,
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

        document_type = info['document_type']
        if document_type == 'batch':
            self._parse_batch_response(response, info)
        elif document_type == 'query':
            self._parse_query_response(response, info)
        else:
            info['errors'].append((ERROR_UNSUPPORTED_DOCUMENT_TYPE, None))

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
               }.get(batch_state_string, None)
            if batch_state is None:
                # as of writing all possible values are implemented for EstadoEnvio
                errors.append((ERROR_MALFORMED_RESPONSE, None))
        info['state'] = batch_state or False

        identification_errors = []
        for element in registration_node.iterfind("tikR:RespuestaLinea", namespaces=namespaces):
            subdoc_errors = []

            # Determine an identifier (`record_key`) for the response line.
            # Sync with function `_get_record_key` from 'l10n_es_edi_verifactu.document'
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
            }.get(status, None)
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
            info['state'] = 'rejected'
            return

        info['state'] = 'accepted'

        raise NotImplementedError
