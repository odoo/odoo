import base64
import json
import requests

from odoo import models, fields
from odoo.tools import html_escape, zeep
from odoo.addons.certificate.tools import CertificateAdapter

EUSKADI_CIPHERS = "DEFAULT:!DH"

AEAT_BASE_URL = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii_1_1/fact/ws"
AEAT_TEST_BASE_URL = "https://prewww1.aeat.es/wlpl/SSII-FACT/ws"

BIZKAIA_BASE_URL = "https://www.bizkaia.eus/ogasuna/sii/documentos"
BIZKAIA_TEST_BASE_URL = "https://pruapps.bizkaia.eus/SSII-FACT/ws"

GIPUZKOA_BASE_URL = "https://egoitza.gipuzkoa.eus/ogasuna/sii/ficheros/v1.1"
GIPUZKOA_TEST_BASE_URL = "https://sii-prep.egoitza.gipuzkoa.eus/JBS/HACI/SSII-FACT/ws"


class L10nEsEdiSiiDocument(models.Model):
    _name = 'l10n_es_edi_sii.document'
    _description = 'SII Document'
    _order = 'create_date desc'

    move_id = fields.Many2one(
        comodel_name='account.move',
        required=True,
        ondelete='cascade',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='move_id.company_id',
    )
    state = fields.Selection(
        selection=[
            ('to_send', "To Send"),
            ('accepted', "Accepted"),
            ('accepted_with_errors', "Accepted with Errors"),
            ('to_cancel', "To Cancel"),
            ('cancelled', "Cancelled"),
        ],
        string="State",
        default='to_send',
        required=True,
    )
    csv = fields.Char(
        string="CSV",
        help="Secure Verification Code returned by the SII",
    )
    attachment_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="SII JSON Payload",
        ondelete='restrict',
        help="The full JSON payload (Header + Body) sent to the SII.",
    )
    response_message = fields.Html(
        string="Response",
    )
    sii_json_file = fields.Binary(
        string="Download JSON",
        compute='_compute_sii_json_file',
    )
    sii_json_filename = fields.Char(
        string="JSON Filename",
        compute='_compute_sii_json_file',
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    def _compute_sii_json_file(self):
        for doc in self:
            doc.sii_json_filename = doc._get_attachment_name()
            if doc.attachment_id:
                doc.sii_json_file = base64.b64encode(doc.attachment_id.raw).decode('utf-8')
            else:
                communication_type = 'A1' if doc.move_id.l10n_es_edi_csv and doc.state != 'to_cancel' else 'A0'
                header = {
                    'IDVersionSii': '1.1',
                    'Titular': {
                        'NombreRazon': doc.company_id.name[:120],
                        'NIF': doc.company_id.vat[2:] if doc.company_id.vat and doc.company_id.vat.startswith('ES') else doc.company_id.vat,
                    },
                    'TipoComunicacion': communication_type,
                }
                info_list = doc.move_id._l10n_es_edi_get_invoices_info()
                full_payload = {'Cabecera': header, 'Cuerpo': info_list}
                json_str = json.dumps(full_payload, indent=4).encode('utf-8')
                doc.sii_json_file = base64.b64encode(json_str).decode('utf-8')

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_attachment_name(self):
        self.ensure_one()
        return f"sii_{self.move_id.name.replace('/', '_')}_{self.id}.json"

    def action_download_json(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/l10n_es_edi_sii.document/{self.id}/sii_json_file?download=true',
            'target': 'self',
        }

    def _get_agency_urls(self):
        document = self[:1]
        agency = document.company_id.l10n_es_sii_tax_agency
        is_sale = document.move_id.is_sale_document()
        BASE_URLS = {
            "aeat":     (AEAT_BASE_URL, AEAT_TEST_BASE_URL),
            "bizkaia":  (BIZKAIA_BASE_URL, BIZKAIA_TEST_BASE_URL),
            "gipuzkoa": (GIPUZKOA_BASE_URL, GIPUZKOA_TEST_BASE_URL),
        }

        if agency not in BASE_URLS:
            return {}

        base_url, test_base_url = BASE_URLS[agency]
        suffix = "Emitidas" if is_sale else "Recibidas"
        test_path = "fe/SiiFactFEV1SOAP" if is_sale else "fr/SiiFactFRV1SOAP"

        return {
            "url": f"{base_url}/SuministroFact{suffix}.wsdl",
            "test_url": f"{test_base_url}/{test_path}",
        }

    # -------------------------------------------------------------------------
    # WEB SERVICE LOGIC
    # -------------------------------------------------------------------------

    def _get_web_service_header(self, communication_type):
        document = self[:1]
        company = document.company_id
        return {
            'IDVersionSii': '1.1',
            'Titular': {
                'NombreRazon': company.name[:120],
                'NIF': company.vat[2:] if company.vat.startswith('ES') else company.vat,
            },
            'TipoComunicacion': communication_type,
        }

    def _post_to_web_service(self, info_list, communication_type='A0'):
        response_results = self._post_to_agency(communication_type, info_list)
        if len(self) == 1:
            response_results = {self: response_results}

        results = {}
        full_payload = {
            'Cabecera': self._get_web_service_header(communication_type),
            'Cuerpo': info_list,
        }
        attachment = self.env['ir.attachment']

        for document, (success, response_data) in response_results.items():
            if response_data.get('error_1117'):
                results[document] = {'error_1117': True}
                continue

            if success:
                state = 'cancelled' if document.state == 'to_cancel' else 'accepted'
                if response_data.get('accepted_with_errors'):
                    state = 'accepted_with_errors'

                response_msg = response_data.get('response_message', self.env._('Success'))

                document.sudo().write({
                    'state': state,
                    'csv': response_data.get('csv'),
                    'response_message': response_msg,
                })

                messages = {
                    'accepted': self.env._("The document was accepted by SII."),
                    'accepted_with_errors': self.env._(
                        "The document was accepted by SII with the following error: %s",
                        response_msg,
                    ),
                    'cancelled': self.env._("The document was cancelled by SII."),
                }
                document.move_id.message_post(body=messages[state])

                if document.state in ('accepted', 'accepted_with_errors'):
                    if not attachment:
                        attachment = self.env['ir.attachment'].sudo().create({
                            'name': document._get_attachment_name(),
                            'raw': json.dumps(full_payload, indent=4).encode('utf-8'),
                            'mimetype': 'application/json',
                            'res_model': 'account.move',
                            'res_id': document.move_id.id,
                        })
                    document.sudo().write({'attachment_id': attachment.id})
            else:
                response_msg = response_data.get('response_message', self.env._('Unknown Error'))

                document.sudo().write({
                    'response_message': response_msg,
                })

                document.move_id.message_post(
                    body=self.env._(
                        "The document was rejected by SII with the following error: %s",
                        response_msg,
                    )
                )

            results[document] = {'success': success, 'state': document.state}

        return results[self] if len(self) == 1 else results

    def _post_to_agency(self, communication_type, info_list):
        document = self[:1]
        company = document.company_id
        connection_vals = self._get_agency_urls()

        def response_for_documents(success, response_data):
            if len(self) == 1:
                return success, response_data
            return {document: (success, response_data) for document in self}

        with requests.Session() as session:
            try:
                session.cert = company.l10n_es_sii_certificate_id
                session.mount('https://', CertificateAdapter(ciphers=EUSKADI_CIPHERS))

                client = zeep.Client(connection_vals['url'], operation_timeout=30, timeout=30, session=session)

                is_sale = document.move_id.is_sale_document()
                service_name = 'SuministroFactEmitidas' if is_sale else 'SuministroFactRecibidas'
                header = self._get_web_service_header(communication_type)
                if company.l10n_es_sii_test_env and not connection_vals.get('test_url'):
                    service_name += 'Pruebas'

                serv = client.bind('siiService', service_name)
                if company.l10n_es_sii_test_env and connection_vals.get('test_url'):
                    serv._binding_options['address'] = connection_vals['test_url']

                if document.state == 'to_cancel':
                    if is_sale:
                        res = serv.AnulacionLRFacturasEmitidas(header, info_list)
                    else:
                        res = serv.AnulacionLRFacturasRecibidas(header, info_list)
                else:
                    if is_sale:
                        res = serv.SuministroLRFacturasEmitidas(header, info_list)
                    else:
                        res = serv.SuministroLRFacturasRecibidas(header, info_list)

            except requests.exceptions.SSLError:
                return response_for_documents(
                    False,
                    {'response_message': self.env._("The SSL certificate could not be validated.")},
                )
            except (zeep.exceptions.Error, requests.exceptions.ConnectionError) as error:
                return response_for_documents(
                    False,
                    {'response_message': self.env._("Networking error:\n%s", error)},
                )
            except Exception as error:  # noqa: BLE001
                return response_for_documents(False, {'response_message': str(error)})

        if not res or not res.RespuestaLinea:
            return response_for_documents(
                False,
                {'response_message': self.env._("The web service is not responding")},
            )

        return self._process_response(res)

    def _process_response(self, res):
        def response_for_documents(success, response_data):
            if len(self) == 1:
                return success, response_data
            return {document: (success, response_data) for document in self}

        resp_state = res["EstadoEnvio"]
        csv_number = res['CSV']

        if resp_state == 'Correcto':
            return response_for_documents(True, {'csv': csv_number, 'response_message': 'Correcto'})

        results = {}
        document = self[:1]
        is_sale = document.move_id.is_sale_document()

        def find_document(respl):
            invoice_number = respl.IDFactura.NumSerieFacturaEmisor
            if is_sale:
                return self.filtered(lambda document: document.move_id.name[:60] == invoice_number)[:1]

            candidates = self.filtered(lambda document: (document.move_id.ref or '')[:60] == invoice_number)
            if len(candidates) <= 1:
                return candidates

            respl_partner_info = respl.IDFactura.IDEmisorFactura
            respl_partner_info_dict = dict(respl_partner_info)
            for candidate in candidates:
                partner = (
                    candidate.move_id.company_id.partner_id
                    if candidate.move_id._l10n_es_is_dua()
                    else candidate.move_id.commercial_partner_id
                )
                partner_info = partner._l10n_es_edi_get_partner_info()
                if partner_info.get('NIF') == respl_partner_info.NIF:
                    return candidate
                if (
                    partner_info.get('IDOtro')
                    and respl_partner_info_dict.get('IDOtro')
                    and all(
                        respl_partner_info_dict['IDOtro'][key] == value
                        for key, value in partner_info['IDOtro'].items()
                    )
                ):
                    return candidate

            return candidates[:1]

        for respl in res.RespuestaLinea:
            document = find_document(respl)
            if not document:
                continue

            resp_line_state = respl.EstadoRegistro
            respl_dict = dict(respl)

            if resp_line_state == 'Correcto':
                results[document] = True, {'csv': csv_number, 'response_message': 'Correcto'}

            elif resp_line_state == 'AceptadoConErrores':
                results[document] = True, {
                    'csv': csv_number,
                    'accepted_with_errors': True,
                    'response_message': self.env._(
                        "Accepted with errors: %s", html_escape(respl.DescripcionErrorRegistro)
                    )
                }

            elif (
                (respl_dict.get('RegistroDuplicado') and respl.RegistroDuplicado.EstadoRegistro == 'Correcta')
                or
                (document.state == 'to_cancel' and respl_dict.get('CodigoErrorRegistro') == 3001)
            ):
                results[document] = True, {
                    'csv': csv_number or document.move_id.l10n_es_edi_csv,
                    'response_message': self.env._("Duplicated/Already processed.")
                }

            elif respl.CodigoErrorRegistro == 1117 and not self.env.context.get('error_1117'):
                return response_for_documents(False, {'error_1117': True})

            else:
                results[document] = False, {
                    'response_message': self.env._("[%(error_code)s] %(error_message)s",
                                        error_code=respl.CodigoErrorRegistro,
                                        error_message=respl.DescripcionErrorRegistro)
                }

        for document in self:
            results.setdefault(document, (False, {'response_message': self.env._("Unknown response state")}))

        return next(iter(results.values())) if len(self) == 1 else results
