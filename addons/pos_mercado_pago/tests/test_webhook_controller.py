import hashlib
import hmac
import json
import uuid
from unittest.mock import patch
from urllib.parse import urlencode

from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo.addons.pos_mercado_pago.models.pos_payment_method import PosPaymentMethod


@tagged('post_install', '-at_install')
class TestMercadoPagoWebhook(TestPointOfSaleHttpCommon):
    """ Verifies the Orders API webhook handler:
    - HMAC-SHA256 against template `id:<data.id LOWERCASE>;request-id:<...>;ts:<...>;`
    - external_reference is parsed from data.external_reference and routes to
      the corresponding pos.session / pos.payment.method
    - rejects bad signatures with 401, malformed payloads with 400
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Setting mp_bearer_token triggers _find_terminal on create, which
        # would hit MP for real — short-circuit it.
        with patch.object(PosPaymentMethod, '_find_terminal', return_value='PAX_A910__SMARTPOS0123456789'):
            cls.method = cls.env['pos.payment.method'].sudo().create({
                'name': 'Mercado Pago test',
                'payment_provider': 'mercado_pago',
                'mp_bearer_token': 'APP_USR-test',
                'mp_webhook_secret_key': 'secret-test',
                'mp_id_point_smart': '1494126963',
            })

        cls.config = cls.env['pos.config'].sudo().create({
            'name': 'MP test config',
            'payment_method_ids': [(4, cls.method.id)],
        })
        cls.config.open_ui()
        cls.session = cls.config.current_session_id
        cls.session.set_opening_control(0, '')

    def _ext_ref(self):
        return f"{self.session.id}_{self.method.id}_{uuid.uuid4()}"

    def _post(self, body, headers, query=None):
        url = '/pos_mercado_pago/notification'
        if query:
            url += '?' + urlencode(query)
        return self.url_open(
            url,
            data=json.dumps(body),
            headers={'Content-Type': 'application/json', **headers},
        )

    def _sign(self, secret, data_id, request_id, ts):
        manifest = f"id:{data_id.lower()};request-id:{request_id};ts:{ts};"
        return hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    def test_valid_webhook_returns_200(self):
        data_id = 'ORD01J67CQQH5904WDBVZEM4JMEP3'
        ext_ref = self._ext_ref()
        body = {'type': 'order', 'action': 'order.processed',
                'data': {'id': data_id,
                         'external_reference': ext_ref,
                         'status': 'processed'}}
        ts = '1700000000'
        request_id = 'req-1'
        v1 = self._sign('secret-test', data_id, request_id, ts)
        resp = self._post(body, {
            'X-Request-Id': request_id,
            'X-Signature': f'ts={ts},v1={v1}',
        }, query={'data.id': data_id, 'data.external_reference': ext_ref, 'type': 'order'})
        self.assertEqual(resp.status_code, 200)

    def test_signature_uses_query_param_data_id(self):
        """ MP signs the `data.id` query param, which the simulator fills with a
        value unrelated to the body's `data.id`. """
        query_data_id = 'ORDTST01KSQRHE278QE8Z79RENQMJ58M'
        ext_ref = self._ext_ref()
        body = {'type': 'order', 'action': 'order.processed',
                'data': {'id': 'ORD01UNRELATEDBODYID',
                         'external_reference': ext_ref,
                         'status': 'processed'}}
        ts = '1700000000'
        request_id = 'req-1'
        v1 = self._sign('secret-test', query_data_id, request_id, ts)
        resp = self._post(body, {
            'X-Request-Id': request_id,
            'X-Signature': f'ts={ts},v1={v1}',
        }, query={'data.id': query_data_id, 'data.external_reference': ext_ref, 'type': 'order'})
        self.assertEqual(resp.status_code, 200)

    @mute_logger('odoo.addons.pos_mercado_pago.controllers.main')
    def test_bad_signature_returns_401(self):
        ext_ref = self._ext_ref()
        body = {'type': 'order', 'action': 'order.action_required',
                'data': {'id': 'ORD01TEST', 'external_reference': ext_ref}}
        resp = self._post(body, {
            'X-Request-Id': 'req-1',
            'X-Signature': 'ts=1700000000,v1=deadbeef',
        }, query={'data.id': 'ORD01TEST', 'data.external_reference': ext_ref, 'type': 'order'})
        self.assertEqual(resp.status_code, 401)

    @mute_logger('odoo.addons.pos_mercado_pago.controllers.main')
    def test_missing_external_reference_returns_400(self):
        body = {'type': 'order', 'data': {'id': 'ORD01TEST'}}
        ts = '1700000000'
        v1 = self._sign('secret-test', 'ORD01TEST', 'req-1', ts)
        resp = self._post(body, {
            'X-Request-Id': 'req-1',
            'X-Signature': f'ts={ts},v1={v1}',
        })
        self.assertEqual(resp.status_code, 400)

    @mute_logger('odoo.addons.pos_mercado_pago.controllers.main')
    def test_missing_signature_returns_400(self):
        body = {'type': 'order', 'data': {'id': 'ORD01TEST',
                                          'external_reference': self._ext_ref()}}
        resp = self._post(body, {'X-Request-Id': 'req-1'})
        self.assertEqual(resp.status_code, 400)

    @mute_logger('odoo.addons.pos_mercado_pago.controllers.main')
    def test_unsupported_type_returns_400(self):
        body = {'type': 'payment', 'data': {'id': '12345'}}
        ts = '1700000000'
        v1 = self._sign('secret-test', '12345', 'req-1', ts)
        resp = self._post(body, {
            'X-Request-Id': 'req-1',
            'X-Signature': f'ts={ts},v1={v1}',
        })
        self.assertEqual(resp.status_code, 400)
