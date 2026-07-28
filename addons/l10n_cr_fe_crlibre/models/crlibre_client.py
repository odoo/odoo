import base64
import logging

import requests

from odoo import models

_logger = logging.getLogger(__name__)

TIMEOUT = 30


class CrlibreApiError(Exception):
    """Error al comunicarse con la API_Hacienda de CRLibre."""


class CrlibreFeClient(models.AbstractModel):
    _name = 'l10n_cr.fe.client'
    _description = 'Cliente HTTP para la API_Hacienda (CRLibre)'

    _ENVIRONMENT_URLS = {
        'stag': ('https://idp.comprobanteselectronicos.go.cr/auth/realms/rut-stag/protocol/openid-connect/token', 'api-stag'),
        'prod': ('https://idp.comprobanteselectronicos.go.cr/auth/realms/rut/protocol/openid-connect/token', 'api-prod'),
    }

    _CLIENT_ID_BY_ENVIRONMENT = {'stag': 'api-stag', 'prod': 'api-prod'}

    def _get_base_url(self):
        url = self.env['ir.config_parameter'].sudo().get_param('l10n_cr_fe.api_url')
        if not url:
            raise CrlibreApiError("Falta configurar 'l10n_cr_fe.api_url'.")
        return url.rstrip('/')

    def _call(self, w, r, params):
        # POST con datos en el body: algunos parametros (XML firmado, certificado en
        # base64) son demasiado grandes para una URL y provocan HTTP 414 si se envian
        # como query string (ver clave/firmarXML/genXML/send). La API lee 'w' de
        # $_POST o $_GET indistintamente (www/api.php), asi que POST funciona para
        # todas las llamadas de este metodo.
        data = dict(params or {})
        data['w'] = w
        data['r'] = r
        url = self._get_base_url() + '/api.php'
        try:
            resp = requests.post(url, data=data, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CrlibreApiError("No se pudo conectar con la API: %s" % exc)
        if resp.status_code != 200:
            raise CrlibreApiError("La API respondió HTTP %s" % resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise CrlibreApiError("La API devolvió una respuesta no-JSON.")
        # La API envuelve todo en {"status": "...", "resp": <datos>} (ver Task 1 / api-samples.md)
        if not isinstance(data, dict) or data.get('status') != 'ok':
            raise CrlibreApiError("La API respondió estado no-ok: %s" % data)
        return data.get('resp')

    def get_clave(self, params):
        resp = self._call('clave', 'clave', params)
        if not isinstance(resp, dict) or not resp.get('clave'):
            raise CrlibreApiError("Respuesta inesperada de 'clave': %s" % resp)
        return {'clave': resp['clave'], 'consecutivo': resp.get('consecutivo', '')}

    def gen_xml_fe(self, params):
        resp = self._call('genXML', 'gen_xml_fe', params)
        if not isinstance(resp, dict) or not resp.get('xml'):
            raise CrlibreApiError("Respuesta inesperada de 'gen_xml_fe': %s" % resp)
        return base64.b64decode(resp['xml']).decode('utf-8')

    def gen_xml_nc(self, params):
        resp = self._call('genXML', 'gen_xml_nc', params)
        if not isinstance(resp, dict) or not resp.get('xml'):
            raise CrlibreApiError("Respuesta inesperada de 'gen_xml_nc': %s" % resp)
        return base64.b64decode(resp['xml']).decode('utf-8')

    def register_api_user(self, full_name, username, password):
        resp = self._call('users', 'users_register', {
            'fullName': full_name,
            'userName': username,
            'email': '%s@l10n-cr-fe.local' % username,
            'about': 'Cuenta de servicio Odoo l10n_cr_fe_crlibre',
            'country': 'crc',
            'pwd': password,
        })
        if not isinstance(resp, dict) or not resp.get('sessionKey'):
            raise CrlibreApiError("Respuesta inesperada de 'users_register': %s" % resp)
        return {'session_key': resp['sessionKey'], 'id_user': resp.get('idUser')}

    def login_api_user(self, username, password):
        resp = self._call('users', 'users_log_me_in', {
            'userName': username,
            'pwd': password,
        })
        if not isinstance(resp, dict) or not resp.get('sessionKey'):
            raise CrlibreApiError("Respuesta inesperada de 'users_log_me_in': %s" % resp)
        return {'session_key': resp['sessionKey'], 'id_user': resp.get('idUser')}

    def _call_multipart(self, w, r, params, files):
        query = dict(params or {})
        query['w'] = w
        query['r'] = r
        url = self._get_base_url() + '/api.php'
        try:
            resp = requests.post(url, params=query, files=files, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CrlibreApiError("No se pudo conectar con la API: %s" % exc)
        if resp.status_code != 200:
            raise CrlibreApiError("La API respondió HTTP %s" % resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise CrlibreApiError("La API devolvió una respuesta no-JSON.")
        if not isinstance(data, dict) or data.get('status') != 'ok':
            raise CrlibreApiError("La API respondió estado no-ok: %s" % data)
        return data.get('resp')

    def upload_certificate(self, session_key, username, p12_bytes):
        resp = self._call_multipart('fileUploader', 'subir_certif', {
            'iam': username,
            'sessionKey': session_key,
        }, files={'fileToUpload': ('certificado.p12', p12_bytes, 'application/x-pkcs12')})
        if not isinstance(resp, dict) or not resp.get('downloadCode'):
            raise CrlibreApiError("Respuesta inesperada de 'subir_certif': %s" % resp)
        return {'download_code': resp['downloadCode']}

    def get_hacienda_token(self, username, password, environment):
        idp_url, client_id = self._ENVIRONMENT_URLS[environment]
        resp = self._call('token', 'gettoken', {
            'url': idp_url,
            'grant_type': 'password',
            'client_id': client_id,
            'client_secret': '',
            'username': username,
            'password': password,
        })
        if not isinstance(resp, dict) or not resp.get('access_token'):
            raise CrlibreApiError("Respuesta inesperada de 'token/gettoken': %s" % resp)
        return resp['access_token']

    def sign_xml(self, download_code, pin, xml):
        xml_b64 = base64.b64encode(xml.encode('utf-8')).decode('ascii')
        resp = self._call('firmarXML', 'firmar', {
            'p12Url': download_code,
            'pinP12': pin,
            'inXml': xml_b64,
        })
        if not isinstance(resp, dict) or not resp.get('xmlFirmado'):
            raise CrlibreApiError("Respuesta inesperada de 'firmarXML/firmar': %s" % resp)
        return base64.b64decode(resp['xmlFirmado']).decode('utf-8')

    def send_fe(self, token, clave, fecha_iso, emisor_tipo, emisor_num,
                receptor_tipo, receptor_num, xml_firmado, environment):
        resp = self._call('send', 'json', {
            'token': token,
            'clave': clave,
            'fecha': fecha_iso,
            'emi_tipoIdentificacion': emisor_tipo,
            'emi_numeroIdentificacion': emisor_num,
            'recp_tipoIdentificacion': receptor_tipo,
            'recp_numeroIdentificacion': receptor_num,
            'comprobanteXml': base64.b64encode(xml_firmado.encode('utf-8')).decode('ascii'),
            'client_id': self._CLIENT_ID_BY_ENVIRONMENT[environment],
        })
        if not isinstance(resp, dict) or 'httpStatus' not in resp:
            raise CrlibreApiError("Respuesta inesperada de 'send/json': %s" % resp)
        http_status = resp['httpStatus']
        if http_status not in (200, 202):
            raise CrlibreApiError("Hacienda rechazó el envío (HTTP %s): %s" % (http_status, resp.get('text')))
        return {'http_status': http_status, 'raw': resp.get('text') or []}

    def consultar_estado(self, token, clave, environment):
        resp = self._call('consultar', 'consultarCom', {
            'token': token,
            'clave': clave,
            'client_id': self._CLIENT_ID_BY_ENVIRONMENT[environment],
        })
        if not isinstance(resp, dict):
            return {'ind_estado': 'desconocido', 'respuesta_xml': None}
        return {
            'ind_estado': resp.get('ind-estado', 'desconocido'),
            'respuesta_xml': resp.get('respuesta-xml'),
        }
