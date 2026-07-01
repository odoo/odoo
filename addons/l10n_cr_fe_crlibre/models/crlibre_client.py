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
