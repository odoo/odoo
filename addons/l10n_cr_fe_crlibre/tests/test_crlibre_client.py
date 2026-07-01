from unittest.mock import patch, MagicMock
from odoo.tests.common import TransactionCase, tagged
from odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client import CrlibreApiError


@tagged('post_install', '-at_install')
class TestCrlibreClient(TransactionCase):

    def setUp(self):
        super().setUp()
        self.client = self.env['l10n_cr.fe.client']
        self.env['ir.config_parameter'].sudo().set_param(
            'l10n_cr_fe.api_url', 'http://host.docker.internal:8080')

    def _mock_response(self, json_data, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.json.return_value = json_data
        return resp

    def test_get_clave_returns_clave_and_consecutivo(self):
        # La API envuelve los datos en {"status":"ok","resp":{...}}
        payload = {'status': 'ok', 'resp': {'clave': '5' * 50, 'consecutivo': '0' * 20, 'length': 50}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.get_clave({'tipoDocumento': 'FE'})
        self.assertEqual(result['clave'], '5' * 50)
        self.assertEqual(result['consecutivo'], '0' * 20)
        m.assert_called_once()

    def test_gen_xml_fe_decodes_base64(self):
        import base64
        xml = '<FacturaElectronica>ok</FacturaElectronica>'
        payload = {'status': 'ok',
                   'resp': {'clave': '5' * 50, 'xml': base64.b64encode(xml.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response(payload)):
            result = self.client.gen_xml_fe({'clave': '5' * 50})
        self.assertEqual(result, xml)

    def test_http_error_raises(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.get',
                   return_value=self._mock_response({}, status=500)):
            with self.assertRaises(CrlibreApiError):
                self.client.get_clave({'tipoDocumento': 'FE'})
