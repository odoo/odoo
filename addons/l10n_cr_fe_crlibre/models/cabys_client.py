import re

import requests

from odoo import models

CABYS_URL = 'https://api.hacienda.go.cr/fe/cabys'
CABYS_CODE_RE = re.compile(r'^\d{13}$')
TIMEOUT = 15


class CabysApiError(Exception):
    """Error al consultar el catálogo CABYS público de Hacienda."""


class CabysClient(models.AbstractModel):
    _name = 'l10n_cr.fe.cabys.client'
    _description = 'Cliente HTTP para el catálogo CABYS de Hacienda'

    def buscar(self, query):
        query = (query or '').strip()
        if CABYS_CODE_RE.match(query):
            params = {'codigo': query}
        elif len(query) >= 3:
            params = {'q': query}
        else:
            raise CabysApiError(
                "Escriba un código CABYS de 13 dígitos o un texto de al menos 3 caracteres.")
        try:
            resp = requests.get(CABYS_URL, params=params, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise CabysApiError("No se pudo conectar con la API de Hacienda: %s" % exc)
        if resp.status_code != 200:
            raise CabysApiError("La API de Hacienda respondió HTTP %s" % resp.status_code)
        try:
            data = resp.json()
        except ValueError:
            raise CabysApiError("La API de Hacienda devolvió una respuesta no-JSON.")
        return self._normalizar(data)

    def _normalizar(self, data):
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get('cabys') or []
        else:
            raise CabysApiError("Respuesta inesperada de la API de Hacienda: %s" % data)
        resultados = []
        for item in items:
            if not isinstance(item, dict) or not item.get('codigo'):
                continue
            resultados.append({
                'codigo': item['codigo'],
                'descripcion': item.get('descripcion', ''),
                'impuesto': float(item.get('impuesto') or 0),
            })
        return resultados
