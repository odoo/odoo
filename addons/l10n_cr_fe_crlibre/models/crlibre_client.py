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

    def _get_base_url(self):
        url = self.env['ir.config_parameter'].sudo().get_param('l10n_cr_fe.api_url')
        if not url:
            raise CrlibreApiError("Falta configurar 'l10n_cr_fe.api_url'.")
        return url.rstrip('/')

    def _call(self, w, r, params):
        query = dict(params or {})
        query['w'] = w
        query['r'] = r
        url = self._get_base_url() + '/api.php'
        try:
            resp = requests.get(url, params=query, timeout=TIMEOUT)
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
