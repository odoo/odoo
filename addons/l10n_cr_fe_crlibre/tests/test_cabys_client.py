from unittest.mock import MagicMock, patch

import requests

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.l10n_cr_fe_crlibre.models.cabys_client import CabysApiError


def _mock_response(status_code=200, json_data=None, raise_json=False):
    resp = MagicMock()
    resp.status_code = status_code
    if raise_json:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_data
    return resp


@tagged('post_install', '-at_install')
class TestCabysClient(TransactionCase):

    def setUp(self):
        super().setUp()
        self.client = self.env['l10n_cr.fe.cabys.client']

    def test_buscar_por_codigo_usa_parametro_codigo(self):
        resp = _mock_response(json_data=[
            {'codigo': '8311100000000', 'descripcion': 'Servicios de consultoría', 'impuesto': 13},
        ])
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp) as mock_get:
            resultados = self.client.buscar('8311100000000')
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs['params'], {'codigo': '8311100000000'})
        self.assertEqual(resultados, [
            {'codigo': '8311100000000', 'descripcion': 'Servicios de consultoría', 'impuesto': 13.0},
        ])

    def test_buscar_por_texto_usa_parametro_q(self):
        resp = _mock_response(json_data={
            'total': 2, 'cantidad': 2,
            'cabys': [
                {'codigo': '2314000991000', 'descripcion': 'Arroz precocido', 'impuesto': 1},
                {'codigo': '2313001000500', 'descripcion': 'Grañones de arroz', 'impuesto': 13},
            ],
        })
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp) as mock_get:
            resultados = self.client.buscar('arroz')
        self.assertEqual(mock_get.call_args.kwargs['params'], {'q': 'arroz'})
        self.assertEqual(len(resultados), 2)
        self.assertEqual(resultados[0]['codigo'], '2314000991000')
        self.assertEqual(resultados[0]['impuesto'], 1.0)

    def test_buscar_texto_corto_lanza_error_sin_llamar_api(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get') as mock_get:
            with self.assertRaises(CabysApiError):
                self.client.buscar('ar')
        mock_get.assert_not_called()

    def test_buscar_timeout_lanza_cabys_api_error(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    side_effect=requests.exceptions.Timeout()):
            with self.assertRaises(CabysApiError):
                self.client.buscar('arroz')

    def test_buscar_http_error_lanza_cabys_api_error(self):
        resp = _mock_response(status_code=500)
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp):
            with self.assertRaises(CabysApiError):
                self.client.buscar('arroz')

    def test_buscar_json_invalido_lanza_cabys_api_error(self):
        resp = _mock_response(raise_json=True)
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp):
            with self.assertRaises(CabysApiError):
                self.client.buscar('arroz')

    def test_buscar_sin_coincidencias_devuelve_lista_vacia(self):
        resp = _mock_response(json_data={'total': 0, 'cantidad': 0, 'cabys': []})
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.cabys_client.requests.get',
                    return_value=resp):
            resultados = self.client.buscar('xyzxyzxyz')
        self.assertEqual(resultados, [])
