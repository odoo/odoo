import base64
import json
import requests

from odoo import api, models, fields
from odoo.tools import html_escape, zeep
from odoo.addons.certificate.tools import CertificateAdapter

EUSKADI_CIPHERS = "DEFAULT:!DH"

AEAT_BASE_URL = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii_1_1/fact/ws"
AEAT_TEST_BASE_URL = "https://prewww1.aeat.es/wlpl/SSII-FACT/ws"

BIZKAIA_BASE_URL = "https://www.bizkaia.eus/ogasuna/sii/documentos"
BIZKAIA_TEST_BASE_URL = "https://pruapps.bizkaia.eus/SSII-FACT/ws"

GIPUZKOA_BASE_URL = "https://egoitza.gipuzkoa.eus/ogasuna/sii/ficheros/v1.1"
GIPUZKOA_TEST_BASE_URL = "https://sii-prep.egoitza.gipuzkoa.eus/JBS/HACI/SSII-FACT/ws"

NAVARRA_BASE_URL = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii/fact/ws"
NAVARRA_ADDRESS = "https://siihacienda.navarra.es/SII_PRODUCCION.proxy/SiiMensajesXsdHandlet.ashx"
NAVARRA_TEST_ADDRESS = "https://siihacienda.navarra.es/SII_PRUEBAS.proxy/SiiMensajesXsdHandlet.ashx"


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
                header = self._get_web_service_header(doc.company_id, communication_type)
                info_list = doc.move_id._l10n_es_edi_get_invoices_info()
                full_payload = {'Cabecera': header, 'Cuerpo': info_list}
                json_str = json.dumps(full_payload, indent=4, ensure_ascii=False).encode('utf-8')
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

    @api.model
    def _get_web_service_header(self, company, communication_type):
        """Returns the common XML header dict required by the SII web service."""
        return {
            'IDVersionSii': '1.1',
            'Titular': {
                'NombreRazon': company.name[:120] if company.name else '',
                'NIF': company.vat[2:] if company.vat and company.vat.startswith('ES') else company.vat,
            },
            'TipoComunicacion': communication_type,
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

        suffix = "Emitidas" if is_sale else "Recibidas"

        if agency == "navarra":
            return {
                "url": f"{NAVARRA_BASE_URL}/SuministroFact{suffix}.wsdl",
                "address": NAVARRA_ADDRESS,
                "test_url": NAVARRA_TEST_ADDRESS,
                "custom_navarra": True,
            }

        if agency not in BASE_URLS:
            return {}

        base_url, test_base_url = BASE_URLS[agency]
        test_path = "fe/SiiFactFEV1SOAP" if is_sale else "fr/SiiFactFRV1SOAP"

        return {
            "url": f"{base_url}/SuministroFact{suffix}.wsdl",
            "test_url": f"{test_base_url}/{test_path}",
        }

    # -------------------------------------------------------------------------
    # WEB SERVICE LOGIC
    # -------------------------------------------------------------------------

    def _post_to_web_service(self, info_list, communication_type='A0'):
        response_results = self._post_to_agency(communication_type, info_list)

        results = {}
        document = self[:1]
        company = document.company_id

        full_payload = {
            'Cabecera': self._get_web_service_header(company, communication_type),
            'Cuerpo': info_list,
        }

        attachment = self.env['ir.attachment']
        for doc, (success, response_data) in response_results.items():
            if response_data.get('error_1117'):
                results[doc] = {'error_1117': True}
                continue

            if success:
                state = 'cancelled' if doc.state == 'to_cancel' else 'accepted'
                if response_data.get('accepted_with_errors'):
                    state = 'accepted_with_errors'

                response_msg = response_data.get('response_message', self.env._('Success'))
                doc.sudo().write({
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
                doc.move_id.message_post(body=messages[state])

                if doc.state in ('accepted', 'accepted_with_errors'):
                    if not attachment:
                        attachment = self.env['ir.attachment'].sudo().create({
                            'name': doc._get_attachment_name(),
                            'raw': json.dumps(full_payload, indent=4, ensure_ascii=False).encode('utf-8'),
                            'mimetype': 'application/json',
                            'res_model': 'account.move',
                            'res_id': doc.move_id.id,
                        })
                    doc.sudo().write({'attachment_id': attachment.id})
            else:
                response_msg = response_data.get('response_message', self.env._('Unknown Error'))
                doc.sudo().write({'response_message': response_msg})
                doc.move_id.message_post(
                    body=self.env._(
                        "The document was rejected by SII with the following error: %s",
                        response_msg,
                    )
                )

            results[doc] = {'success': success, 'state': doc.state}

        return results

    def _post_to_agency(self, communication_type, info_list):
        document = self[:1]
        company = document.company_id
        connection_vals = self._get_agency_urls()

        def response_for_documents(success, response_data):
            return {doc: (success, response_data) for doc in self}

        with requests.Session() as session:
            try:
                session.cert = company.l10n_es_sii_certificate_id
                session.mount('https://', CertificateAdapter(ciphers=EUSKADI_CIPHERS))

                client = zeep.Client(connection_vals['url'], operation_timeout=30, timeout=30, session=session)

                is_sale = document.move_id.is_sale_document()
                service_name = 'SuministroFactEmitidas' if is_sale else 'SuministroFactRecibidas'
                header = self._get_web_service_header(company, communication_type)

                if connection_vals.get('custom_navarra'):
                    header['_attributes'] = {
                        'xmlns:sum': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii/fact/ws/SuministroLR.xsd',
                        'xmlns:sum1': 'https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/ssii/fact/ws/SuministroInformacion.xsd',
                    }

                if company.l10n_es_sii_test_env and not connection_vals.get('test_url'):
                    service_name += 'Pruebas'

                serv = client.bind('siiService', service_name)

                if company.l10n_es_sii_test_env and connection_vals.get('test_url'):
                    serv._binding_options['address'] = connection_vals['test_url']

                elif not company.l10n_es_sii_test_env and connection_vals.get('address'):
                    serv._binding_options['address'] = connection_vals['address']

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
                return response_for_documents(False, {'response_message': self.env._("The SSL certificate could not be validated.")})
            except (zeep.exceptions.Error, requests.exceptions.ConnectionError) as error:
                return response_for_documents(False, {'response_message': self.env._("Networking error:\n%s", error)})
            except Exception as error:  # noqa: BLE001
                return response_for_documents(False, {'response_message': str(error)})

        if not res or not res.RespuestaLinea:
            return response_for_documents(False, {'response_message': self.env._("The web service is not responding")})

        return self._process_response(res)

    def _process_response(self, res):
        def response_for_documents(success, response_data):
            return {doc: (success, response_data) for doc in self}

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
                return self.filtered(lambda d: d.move_id.name[:60] == invoice_number)[:1]

            candidates = self.filtered(lambda d: (d.move_id.ref or '')[:60] == invoice_number)
            if len(candidates) <= 1:
                return candidates

            respl_partner_info = respl.IDFactura.IDEmisorFactura
            for candidate in candidates:
                partner = candidate.move_id.company_id.partner_id if candidate.move_id._l10n_es_is_dua() else candidate.move_id.commercial_partner_id
                partner_info = partner._l10n_es_edi_get_partner_info()
                if partner_info.get('NIF') == respl_partner_info.NIF:
                    return candidate
            return candidates[:1]

        for respl in res.RespuestaLinea:
            doc = find_document(respl)
            if not doc:
                continue

            resp_line_state = respl.EstadoRegistro
            respl_dict = dict(respl)

            line_csv = respl_dict.get('CSV') or csv_number

            if resp_line_state == 'Correcto':
                results[doc] = True, {'csv': line_csv, 'response_message': 'Correcto'}

            elif resp_line_state == 'AceptadoConErrores':
                results[doc] = True, {
                    'csv': line_csv,
                    'accepted_with_errors': True,
                    'response_message': self.env._(
                        "Accepted with errors: %s", html_escape(respl.DescripcionErrorRegistro)
                    )
                }

            elif (
                (respl_dict.get('RegistroDuplicado') and respl.RegistroDuplicado.EstadoRegistro == 'Correcta')
                or
                (doc.state == 'to_cancel' and respl_dict.get('CodigoErrorRegistro') == 3001)
            ):
                results[doc] = True, {
                    'csv': line_csv or doc.move_id.l10n_es_edi_csv,
                    'response_message': self.env._("Duplicated/Already processed.")
                }

            elif respl.CodigoErrorRegistro == 1117 and not self.env.context.get('error_1117'):
                results[doc] = False, {'error_1117': True}

            else:
                results[doc] = False, {
                    'response_message': self.env._("[%(error_code)s] %(error_message)s",
                                        error_code=respl.CodigoErrorRegistro,
                                        error_message=respl.DescripcionErrorRegistro)
                }

        for doc in self:
            results.setdefault(doc, (False, {'response_message': self.env._("Unknown response state")}))

        return results
