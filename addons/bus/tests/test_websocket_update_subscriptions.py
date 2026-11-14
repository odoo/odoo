# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import new_test_user

from odoo.addons.bus.bus_dispatcher import dispatch
from odoo.addons.bus.tests.common import WebsocketCase


class TestWebsocketUpdateSubscriptions(WebsocketCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.alice_user = new_test_user(cls.env, login="alice_user", password="Password!1")
        cls.bob_user = new_test_user(cls.env, login="bob_user", password="Password!1")

    def setUp(self):
        super().setUp()
        self.bob_custom = (self.env.cr.dbname, "res.users", self.bob_user.id, "custom")

    def test_join_and_leave(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.alice_user._bus_join((self.bob_user, "custom"))
        # Sent in the same transaction, after the join: received.
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertEqual(self.recv_types_until(websocket, "bob_row"), ["bob_row"])
        self.alice_user._bus_leave(self.bob_user)
        # The leave and ``alice_row`` share a batch. The single worker of the tests
        # applies the leave before the batch of ``alice_row_2``.
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        # The change itself is never sent to the client.
        self.assertEqual(self.recv_types_until(websocket, "alice_row"), ["alice_row"])
        self.alice_user._bus_send("alice_row_2", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row_2")
        self.assertNotIn(self.bob_custom, dispatch._topic_by_channel)

    def test_leave_subchannel(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertEqual(self.recv_types_until(websocket, "bob_row"), ["bob_row"])
        self.alice_user._bus_leave((self.bob_user, "custom"))
        # The leave and ``alice_row`` share a batch. The single worker of the tests
        # applies the leave before the batch of ``alice_row_2``.
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        # The change itself is never sent to the client.
        self.assertEqual(self.recv_types_until(websocket, "alice_row"), ["alice_row"])
        self.alice_user._bus_send("alice_row_2", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row_2")
        self.assertNotIn(self.bob_custom, dispatch._topic_by_channel)

    def test_join_subchannel_then_leave_record(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.alice_user._bus_leave(self.bob_user)
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row")
        # The single worker of the tests applies the change before the next batch.
        self.alice_user._bus_send("alice_row_2", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row_2")
        # Frames of different channels come in no given order: only the topic proves it.
        self.assertNotIn(self.bob_custom, dispatch._topic_by_channel)

    def test_leave_record_then_join_subchannel(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.trigger_notification_dispatching()
        # Changes are applied in call order: the join comes last, it wins.
        self.alice_user._bus_leave(self.bob_user)
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertEqual(self.recv_types_until(websocket, "bob_row"), ["bob_row"])

    def test_join_not_bus_channel(self):
        # A partner sends on its users: joining it in their place must be explicit.
        with self.assertRaises(ValueError):
            self.alice_user._bus_join((self.bob_user.partner_id, "custom"))
        with self.assertRaises(ValueError):
            self.alice_user.partner_id._bus_join(self.bob_user)
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.alice_user._bus_join(
            *((user, "custom") for user in self.bob_user.partner_id._bus_channels()),
        )
        self.bob_user.partner_id._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertEqual(self.recv_types_until(websocket, "bob_row"), ["bob_row"])

    def test_notify_missed(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.env.cr.precommit.run()
        self.env.cr.postcommit.clear()  # NOTIFY lost: the next change catches it up.
        self.alice_user._bus_join(self.bob_user)
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertEqual(self.recv_types_until(websocket, "bob_row"), ["bob_row"])

    def test_connect_catches_up_join(self):
        self._reset_bus()
        last = self.env["bus.bus"]._bus_last_id()
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.trigger_notification_dispatching()
        # Connected after the join, which is after ``last``: caught up like any notification.
        session = self.authenticate("alice_user", "Password!1")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        self.subscribe(websocket, last=last)
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertEqual(self.recv_types_until(websocket, "bob_row"), ["bob_row"])

    def test_resubscribe_with_channels_read_before_join(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        last = self.env["bus.bus"]._bus_last_id()
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertEqual(self.recv_types_until(websocket, "bob_row"), ["bob_row"])
        # Channels read before the join, which is applied: the join is caught up again.
        self.subscribe(websocket, last=last)
        self.bob_user._bus_send("bob_row_2", None, subchannel="custom")
        self.trigger_notification_dispatching()
        # The first row is sent again by the catch-up of the join: the client skips it.
        self.assertIn("bob_row_2", self.recv_types_until(websocket, "bob_row_2"))

    def test_resubscribe_with_channels_read_before_older_join(self):
        websocket = self.connect_and_subscribe("alice_user", "Password!1")
        self.alice_user._bus_join((self.bob_user, "custom"))
        self.trigger_notification_dispatching()
        self.alice_user._bus_send("alice_row", None)
        self.trigger_notification_dispatching()
        self.recv_types_until(websocket, "alice_row")
        # As if the join committed late: older than ``last``, applied after the channels
        # were read. It is still in the history: caught up again.
        self.subscribe(websocket, last=self.env["bus.bus"]._bus_last_id())
        self.bob_user._bus_send("bob_row", None, subchannel="custom")
        self.trigger_notification_dispatching()
        self.assertIn("bob_row", self.recv_types_until(websocket, "bob_row"))
