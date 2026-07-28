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
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
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
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)):
            result = self.client.gen_xml_fe({'clave': '5' * 50})
        self.assertEqual(result, xml)

    def test_http_error_raises(self):
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response({}, status=500)):
            with self.assertRaises(CrlibreApiError):
                self.client.get_clave({'tipoDocumento': 'FE'})

    def test_register_api_user_returns_session(self):
        payload = {'status': 'ok', 'resp': {'sessionKey': 'sk123', 'userName': 'empresa1', 'idUser': 5}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.register_api_user('Empresa Uno', 'empresa1', 'pass123')
        self.assertEqual(result['session_key'], 'sk123')
        self.assertEqual(result['id_user'], 5)
        called_data = m.call_args.kwargs['data']
        self.assertEqual(called_data['w'], 'users')
        self.assertEqual(called_data['r'], 'users_register')
        self.assertEqual(called_data['userName'], 'empresa1')

    def test_register_api_user_already_exists_raises(self):
        payload = {'status': 'ok', 'resp': {'code': '-304', 'status': 'usuario ya existe'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.register_api_user('Empresa Uno', 'empresa1', 'pass123')

    def test_login_api_user_returns_session(self):
        payload = {'status': 'ok', 'resp': {'sessionKey': 'sk456', 'userName': 'empresa1', 'idUser': 5}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.login_api_user('empresa1', 'pass123')
        self.assertEqual(result['session_key'], 'sk456')
        called_data = m.call_args.kwargs['data']
        self.assertEqual(called_data['r'], 'users_log_me_in')

    def test_upload_certificate_returns_download_code(self):
        payload = {'status': 'ok', 'resp': {'idFile': 1, 'name': 'cert.p12', 'downloadCode': 'DC123'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.upload_certificate('sk123', 'empresa1', b'contenido-p12')
        self.assertEqual(result['download_code'], 'DC123')
        called_params = m.call_args.kwargs['params']
        self.assertEqual(called_params['w'], 'fileUploader')
        self.assertEqual(called_params['r'], 'subir_certif')
        self.assertEqual(called_params['iam'], 'empresa1')
        self.assertEqual(called_params['sessionKey'], 'sk123')
        called_files = m.call_args.kwargs['files']
        self.assertIn('fileToUpload', called_files)

    def test_get_hacienda_token_returns_access_token(self):
        payload = {'status': 'ok', 'resp': {
            'access_token': 'tok123', 'expires_in': 300, 'refresh_token': 'ref123'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            token = self.client.get_hacienda_token('user@stag.comprobanteselectronicos.go.cr', 'pass', 'stag')
        self.assertEqual(token, 'tok123')
        called_data = m.call_args.kwargs['data']
        self.assertEqual(called_data['w'], 'token')
        self.assertEqual(called_data['r'], 'gettoken')
        self.assertEqual(called_data['client_id'], 'api-stag')
        self.assertIn('idp.comprobanteselectronicos.go.cr', called_data['url'])

    def test_get_hacienda_token_prod_uses_prod_client_id(self):
        payload = {'status': 'ok', 'resp': {'access_token': 'tokprod'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            self.client.get_hacienda_token('user@prod...', 'pass', 'prod')
        self.assertEqual(m.call_args.kwargs['data']['client_id'], 'api-prod')

    def test_get_hacienda_token_missing_access_token_raises(self):
        payload = {'status': 'ok', 'resp': None}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.get_hacienda_token('user', 'pass', 'stag')

    def test_sign_xml_decodes_base64(self):
        import base64
        xml_firmado = '<FacturaElectronica>firmado</FacturaElectronica>'
        payload = {'status': 'ok', 'resp': {'xmlFirmado': base64.b64encode(xml_firmado.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.sign_xml('DC123', '1234', '<FacturaElectronica>sin firmar</FacturaElectronica>')
        self.assertEqual(result, xml_firmado)
        called_data = m.call_args.kwargs['data']
        self.assertEqual(called_data['w'], 'firmarXML')
        self.assertEqual(called_data['r'], 'firmar')
        self.assertEqual(called_data['p12Url'], 'DC123')
        self.assertEqual(called_data['pinP12'], '1234')
        self.assertEqual(
            called_data['inXml'],
            base64.b64encode('<FacturaElectronica>sin firmar</FacturaElectronica>'.encode()).decode())

    def test_sign_xml_missing_result_raises(self):
        payload = {'status': 'ok', 'resp': {}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.sign_xml('DC123', '1234', '<xml/>')

    def test_send_fe_parses_202_recibido(self):
        raw_lines = ['HTTP/1.1 202 Accepted', 'Content-Type: application/json', '', '']
        payload = {'status': 'ok', 'resp': {'httpStatus': 202, 'text': raw_lines}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.send_fe(
                token='tok', clave='5' * 50, fecha_iso='2026-07-06T09:00:00-06:00',
                emisor_tipo='01', emisor_num='702320717',
                receptor_tipo='01', receptor_num='102340567',
                xml_firmado='<FacturaElectronica/>', environment='stag')
        self.assertEqual(result['http_status'], 202)
        called_data = m.call_args.kwargs['data']
        self.assertEqual(called_data['w'], 'send')
        self.assertEqual(called_data['r'], 'json')
        self.assertEqual(called_data['client_id'], 'api-stag')
        self.assertEqual(called_data['token'], 'tok')

    def test_send_fe_error_status_raises(self):
        payload = {'status': 'ok', 'resp': {'httpStatus': 400, 'text': ['HTTP/1.1 400 Bad Request', '']}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)):
            with self.assertRaises(CrlibreApiError):
                self.client.send_fe(
                    token='tok', clave='5' * 50, fecha_iso='2026-07-06T09:00:00-06:00',
                    emisor_tipo='01', emisor_num='702320717',
                    receptor_tipo='01', receptor_num='102340567',
                    xml_firmado='<FacturaElectronica/>', environment='stag')

    def test_consultar_estado_aceptado(self):
        payload = {'status': 'ok', 'resp': {'ind-estado': 'aceptado', 'respuesta-xml': 'PGZvbz8+'}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.consultar_estado('tok', '5' * 50, 'stag')
        self.assertEqual(result['ind_estado'], 'aceptado')
        self.assertEqual(result['respuesta_xml'], 'PGZvbz8+')
        self.assertEqual(m.call_args.kwargs['data']['client_id'], 'api-stag')

    def test_consultar_estado_pendiente(self):
        payload = {'status': 'ok', 'resp': None}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)):
            result = self.client.consultar_estado('tok', '5' * 50, 'stag')
        self.assertEqual(result['ind_estado'], 'desconocido')
        self.assertIsNone(result['respuesta_xml'])

    def test_gen_xml_nc_decodes_base64(self):
        import base64
        xml = '<NotaCreditoElectronica>ok</NotaCreditoElectronica>'
        payload = {'status': 'ok',
                   'resp': {'clave': '5' * 50, 'xml': base64.b64encode(xml.encode()).decode()}}
        with patch('odoo.addons.l10n_cr_fe_crlibre.models.crlibre_client.requests.post',
                   return_value=self._mock_response(payload)) as m:
            result = self.client.gen_xml_nc({'clave': '5' * 50})
        self.assertEqual(result, xml)
        self.assertEqual(m.call_args.kwargs['data']['r'], 'gen_xml_nc')
