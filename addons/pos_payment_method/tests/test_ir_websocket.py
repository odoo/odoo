from unittest.mock import MagicMock, patch

from odoo.tests import TransactionCase, new_test_user


class TestIrWebsocket(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_method = cls.env["pos.electronic.payment"].create({
            "name": "Test",
            "payment_provider": "Test",
            "integration_type": "terminal",
        })
        cls.payment_method_user = new_test_user(
            cls.env, login="test_payment_method_user", groups="pos_payment_method.group_payment_method_user,base.group_user",
        )
        cls.other_user = new_test_user(
            cls.env, login="test_other_user", groups="base.group_user",
        )

    def _call_build_bus_channel_list(self, user, channels: list[str]):
        mock_wsrequest = MagicMock()
        mock_wsrequest.session.uid = user.id
        with patch("odoo.addons.bus.models.ir_websocket.wsrequest", new=mock_wsrequest):
            ir_websocket_model = self.env["ir.websocket"].with_user(user)
            return set(ir_websocket_model._build_bus_channel_list(channels))

    def test_electronic_payment_record_added_if_user_has_access(self):
        channels = self._call_build_bus_channel_list(self.payment_method_user, [f"pos.electronic.payment:{self.payment_method.id}"])
        self.assertIn(self.payment_method, channels)

    def test_no_record_added_if_user_has_no_access(self):
        channels = self._call_build_bus_channel_list(self.other_user, [f"pos.electronic.payment:{self.payment_method.id}"])
        self.assertNotIn(self.payment_method, channels)

    def test_no_record_added_if_record_does_not_exist(self):
        channels = self._call_build_bus_channel_list(self.other_user, ["pos.electronic.payment:999999"])
        self.assertNotIn(self.env["pos.electronic.payment"].browse(999999), channels)
