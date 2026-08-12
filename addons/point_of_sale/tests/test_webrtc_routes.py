import uuid
from unittest.mock import patch

from odoo.tests import JsonRpcException, tagged

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

_NOTIFY_PATH = "odoo.addons.point_of_sale.models.pos_bus_mixin.PosBusMixin._notify"


@tagged('post_install', '-at_install')
class TestWebrtcRoutes(TestPointOfSaleHttpCommon):
    def test_terminal_route_requires_pos_user(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        peer_id = str(uuid.uuid4())

        # not logged in
        with self.assertRaises(JsonRpcException, msg='odoo.exceptions.AccessError'):
            self.make_jsonrpc_request('/pos/webrtc/announce', {
                'config_id': self.main_pos_config.id,
                'peer_id': peer_id,
            })

        # logged in as a pos user
        self.authenticate(self.pos_user.login, self.pos_user.login)
        result = self.make_jsonrpc_request('/pos/webrtc/announce', {
            'config_id': self.main_pos_config.id,
            'peer_id': peer_id,
        })
        self.assertEqual(result['peer_group'], 'terminal')

        # backend force peer_group to be 'terminal'
        result = self.make_jsonrpc_request('/pos/webrtc/announce', {
            'config_id': self.main_pos_config.id,
            'peer_id': peer_id,
            'peer_group': 'customer_display',
        })
        self.assertEqual(result['peer_group'], 'terminal')

    def test_customer_display_route_ignores_client_identity(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        peer_id = str(uuid.uuid4())

        # not logged in: only access_token is required for customer_display
        result = self.make_jsonrpc_request('/pos_customer_display/webrtc/announce', {
            'access_token': self.main_pos_config.access_token,
            'peer_id': peer_id,
        })
        self.assertEqual(result['peer_group'], 'customer_display')

        # backend force peer_group to be 'customer_display'
        result = self.make_jsonrpc_request('/pos_customer_display/webrtc/announce', {
            'access_token': self.main_pos_config.access_token,
            'peer_id': peer_id,
            'peer_group': 'terminal',
        })
        self.assertEqual(result['peer_group'], 'customer_display')

        # invalid access_token
        with self.assertRaises(JsonRpcException, msg='werkzeug.exceptions.Unauthorized'):
            self.make_jsonrpc_request('/pos_customer_display/webrtc/announce', {
                'access_token': 'not-the-real-token',
                'peer_id': peer_id,
            })

    def test_signal_routes_stamp_group_from_the_authenticated_route_not_the_message(self):
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.authenticate(self.pos_user.login, self.pos_user.login)

        msg = {
            'type': 'ice',
            'from': 'a',
            'to': 'b',
            'candidate': {'candidate': 'candidate:...'},
            'group': 'customer_display',  # smuggled: this route should still stamp "terminal"
        }
        with patch(_NOTIFY_PATH) as mock:
            self.make_jsonrpc_request('/pos/webrtc/signal', {
                'config_id': self.main_pos_config.id,
                'msg': msg,
            })
        mock.assert_called_once_with('WEBRTC_SIGNAL', {**msg, 'group': 'terminal'})

        msg = {
            'type': 'ice',
            'from': 'a',
            'to': 'b',
            'candidate': {'candidate': 'candidate:...'},
            'group': 'terminal',  # smuggled: this route should still stamp "customer_display"
        }
        with patch(_NOTIFY_PATH) as mock:
            self.make_jsonrpc_request('/pos_customer_display/webrtc/signal', {
                'access_token': self.main_pos_config.access_token,
                'msg': msg,
            })
        mock.assert_called_once_with('WEBRTC_SIGNAL', {**msg, 'group': 'customer_display'})
