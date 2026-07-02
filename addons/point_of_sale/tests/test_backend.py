import uuid
from unittest.mock import patch

import odoo
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.point_of_sale.models.pos_payment_method import PosPaymentMethod
from odoo.addons.point_of_sale.tests.common import TestPoSCommon

_NOTIFY_PATH = "odoo.addons.point_of_sale.models.pos_bus_mixin.PosBusMixin._notify"


@odoo.tests.tagged('post_install', '-at_install')
class TestBackend(TestPoSCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.non_pos_user = cls.env["res.users"].create({
            'name': 'Non-PoS Test User',
            'login': 'non_pos_user',
            'password': 'non_pos_user',
            'group_ids': [
                (4, cls.env.ref('base.group_user').id),
            ],
        })

    def test_onchange_payment_provider(self):
        pm = self.env['pos.payment.method'].create({'name': 'Test PM'})
        with patch.object(PosPaymentMethod, '_get_terminal_provider_selection', return_value=[('terminal_1', 'Terminal 1'), ('terminal_2', 'Terminal 2')]), \
             patch.object(PosPaymentMethod, '_get_external_qr_provider_selection', return_value=[('qr_1', 'QR Code 1'), ('qr_2', 'QR Code 2')]), \
             patch.object(PosPaymentMethod, '_get_cash_machine_selection', return_value=[('cash_1', 'Cash Machine 1'), ('cash_2', 'Cash Machine 2')]):
            # False --> terminal_1 = terminal
            pm.payment_provider = 'terminal_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_1 --> terminal_2 = terminal
            pm.payment_provider = 'terminal_2'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_2 --> qr_1 = external_qr
            pm.payment_provider = 'qr_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_1 --> qr_2 = external_qr
            pm.payment_provider = 'qr_2'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_2 --> False = external_qr
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # False --> qr_1 = external_qr
            pm.payment_provider = 'qr_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'external_qr')

            # qr_1 --> cash_1 = cash_machine
            pm.payment_provider = 'cash_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'cash_machine')

            # cash_1 --> terminal_1 = terminal
            pm.payment_provider = 'terminal_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # terminal_1 --> False = terminal
            pm.payment_provider = False
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'terminal')

            # False --> cash_1 = cash_machine
            pm.payment_provider = 'cash_1'
            pm._onchange_payment_provider()
            self.assertEqual(pm.payment_method_type, 'cash_machine')

    def test_onchange_payment_method_type(self):
        pm = self.env['pos.payment.method'].create({'name': 'Test PM'})
        with patch.object(PosPaymentMethod, '_get_terminal_provider_selection', return_value=[('terminal_1', 'Terminal 1'), ('terminal_2', 'Terminal 2')]), \
             patch.object(PosPaymentMethod, '_get_external_qr_provider_selection', return_value=[('qr_1', 'QR Code 1'), ('qr_2', 'QR Code 2')]), \
             patch.object(PosPaymentMethod, '_get_cash_machine_selection', return_value=[('cash_1', 'Cash Machine 1'), ('cash_2', 'Cash Machine 2')]):
            # (False) none --> terminal = False
            pm.payment_method_type = 'terminal'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> external_qr = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'external_qr'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (qr_1) external_qr --> terminal = False
            pm.payment_provider = 'qr_1'
            pm.payment_method_type = 'terminal'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> cash_machine = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'cash_machine'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

            # (terminal_1) terminal --> none = False
            pm.payment_provider = 'terminal_1'
            pm.payment_method_type = 'none'
            pm._onchange_payment_method_type()
            self.assertFalse(pm.payment_provider)

    def test_notify_synchronisation(self):
        with patch(_NOTIFY_PATH) as mock:
            self.basic_config.notify_synchronisation()
            self.basic_config.notify_synchronisation(records={"pos.order": [{"id": 1}]})
            self.basic_config.notify_synchronisation(deleted_record_ids={"pos.order": [1, 2]})
            self.basic_config.notify_synchronisation(
                records={"pos.order": [{"id": 1}]},
                deleted_record_ids={"pos.order": [2]},
            )

        calls = [c.args for c in mock.mock_calls]
        self.assertEqual(
            sum(1 for args in calls if args and args[0] == "SERVER_SYNCHRONISATION"),
            3,
        )
        self.assertIn(
            ("SERVER_SYNCHRONISATION", {"records": {"pos.order": [{"id": 1}]}}),
            calls,
        )
        self.assertIn(
            ("SERVER_SYNCHRONISATION", {"deleted_record_ids": {"pos.order": [1, 2]}}),
            calls,
        )
        self.assertIn(
            ("SERVER_SYNCHRONISATION", {
                "records": {"pos.order": [{"id": 1}]},
                "deleted_record_ids": {"pos.order": [2]},
            }),
            calls,
        )

    def test_webrtc_announce(self):
        # no active session is rejected
        with self.assertRaises(AccessError):
            self.basic_config.webrtc_announce(str(uuid.uuid4()), "terminal")

        self.basic_config.open_ui()

        # happy path without device_uuid: peer_device_uuid is None in notification
        peer_id = str(uuid.uuid4())
        with patch(_NOTIFY_PATH) as mock:
            result = self.basic_config.webrtc_announce(peer_id, "terminal")
        self.assertEqual(result["uuid"], peer_id)
        self.assertEqual(result["bus_channel"], self.basic_config.access_token)
        self.assertEqual(result["peer_group"], "terminal")
        mock.assert_called_once_with("WEBRTC_PEER_ANNOUNCE", {
            "peer_id": peer_id,
            "peer_group": "terminal",
            "peer_device_uuid": None,
        })

        # device_uuid is forwarded to notification
        peer_id = str(uuid.uuid4())
        device_uuid = str(uuid.uuid4())
        with patch(_NOTIFY_PATH) as mock:
            self.basic_config.webrtc_announce(peer_id, "terminal", device_uuid)
        mock.assert_called_once_with("WEBRTC_PEER_ANNOUNCE", {
            "peer_id": peer_id,
            "peer_group": "terminal",
            "peer_device_uuid": device_uuid,
        })

        # invalid device_uuid is rejected
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_announce(str(uuid.uuid4()), "terminal", "not-a-uuid")

        # all valid peer groups are accepted
        for group in ("terminal", "customer_display"):
            with self.subTest(group=group):
                result = self.basic_config.webrtc_announce(str(uuid.uuid4()), group)
                self.assertEqual(result["peer_group"], group)

        # non-POS user is rejected
        with self.assertRaises(AccessError):
            self.basic_config.with_user(self.non_pos_user).webrtc_announce(str(uuid.uuid4()), "terminal")

        # invalid UUID is rejected
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_announce("not-a-uuid", "terminal")

        # invalid peer group is rejected
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_announce(str(uuid.uuid4()), "invalid_group")

    def test_webrtc_signal(self):
        # no active session is rejected
        with self.assertRaises(AccessError):
            self.basic_config.webrtc_signal({"type": "offer", "from": "a", "to": "b", "sdp": {}})

        self.basic_config.open_ui()

        # offer: valid, notifies with full message
        msg = {"type": "offer", "from": "a", "to": "b", "sdp": {"type": "offer", "sdp": "v=0"}}
        with patch(_NOTIFY_PATH) as mock:
            self.basic_config.webrtc_signal(msg)
        mock.assert_called_once_with("WEBRTC_SIGNAL", msg)

        # answer: valid
        msg = {"type": "answer", "from": "a", "to": "b", "sdp": {"type": "answer", "sdp": "v=0"}}
        with patch(_NOTIFY_PATH) as mock:
            self.basic_config.webrtc_signal(msg)
        mock.assert_called_once_with("WEBRTC_SIGNAL", msg)

        # ice: valid
        msg = {"type": "ice", "from": "a", "to": "b", "candidate": {"candidate": "candidate:..."}}
        with patch(_NOTIFY_PATH) as mock:
            self.basic_config.webrtc_signal(msg)
        mock.assert_called_once_with("WEBRTC_SIGNAL", msg)

        # non-POS user is rejected
        with self.assertRaises(AccessError):
            self.basic_config.with_user(self.non_pos_user).webrtc_signal({"type": "offer", "from": "a", "to": "b", "sdp": {}})

        # invalid signal type is rejected
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_signal({"type": "hack", "from": "a", "to": "b"})

        # offer/answer without sdp is rejected
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_signal({"type": "offer", "from": "a", "to": "b"})
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_signal({"type": "answer", "from": "a", "to": "b"})

        # ice without candidate is rejected
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_signal({"type": "ice", "from": "a", "to": "b"})

        # missing from/to is rejected
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_signal({"type": "offer", "to": "b", "sdp": {}})
        with self.assertRaises(ValidationError):
            self.basic_config.webrtc_signal({"type": "offer", "from": "a", "sdp": {}})
