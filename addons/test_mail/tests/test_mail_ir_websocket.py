import json
from odoo.tests import new_test_user, tagged
from odoo.addons.bus.tests.common import WebsocketCase
from odoo.addons.bus.models.bus import channel_with_db, json_dump


@tagged("-at_install", "post_install")
class TestIrWebsocket(WebsocketCase):
    def test_chatter_channel_list(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        session = self.authenticate("bob_user", "bob_user")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        test_mail = self.env["mail.test.simple"].create({
            "name": "Test",
            "email_from": "tutu@test.com",
        })
        self.subscribe(
            websocket,
            [f"model-{test_mail._name}_{test_mail.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        test_mail.message_post(
            body="Test message",
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_comment").id,
            author_id=bob.partner_id.id,
        )
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.trigger_notification_dispatching([(test_mail, "thread"), (test_mail, "thread-internal")])
        notifications = json.loads(websocket.recv())
        message_notifications = [notification for notification in notifications if notification["message"]["type"] == "mail.message/new"]
        self.assertEqual(len(message_notifications), 1)
        notification = message_notifications[0]
        self._close_websockets()
        bus_record = self.env["bus.bus"].search([("id", "=", int(notification["id"]))])
        self.assertEqual(bus_record.channel, json_dump(channel_with_db(self.env.cr.dbname, (test_mail, "thread"))))
        self.assertEqual(notification["message"]["type"], "mail.message/new")

    def test_chatter_channel_list_internal(self):
        bob = new_test_user(self.env, login="bob_user", groups="base.group_user")
        session = self.authenticate("bob_user", "bob_user")
        websocket = self.websocket_connect(cookie=f"session_id={session.sid};")
        test_mail = self.env["mail.test.simple"].create({
            "name": "Test",
            "email_from": "tutu@test.com",
        })
        self.subscribe(
            websocket,
            [f"model-{test_mail._name}_{test_mail.id}"],
            self.env["bus.bus"]._bus_last_id(),
        )
        test_mail.message_post(
            body="Test message",
            message_type="comment",
            subtype_id=self.env.ref("mail.mt_note").id,
            author_id=bob.partner_id.id,
        )
        self.env.cr.precommit.run()  # trigger the creation of bus.bus records
        self.trigger_notification_dispatching([(test_mail, "thread"), (test_mail, "thread-internal")])
        notifications = json.loads(websocket.recv())
        message_notifications = [notification for notification in notifications if notification["message"]["type"] == "mail.message/new"]
        self.assertEqual(len(message_notifications), 1)
        notification = message_notifications[0]
        self._close_websockets()
        bus_record = self.env["bus.bus"].search([("id", "=", int(notification["id"]))])
        self.assertEqual(bus_record.channel, json_dump(channel_with_db(self.env.cr.dbname, (test_mail, "thread-internal"))))
        self.assertEqual(notification["message"]["type"], "mail.message/new")
