# Copyright 2016 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import exceptions
from odoo.tests import common

from ..models.res_users import DANGER, DEFAULT, INFO, SUCCESS, WARNING


class TestResUsers(common.TransactionCase):
    def test_notify_success(self):
        bus_bus = self.env["bus.bus"]
        domain = [("channel", "=", self.env.user.notify_success_channel_name)]
        existing = bus_bus.search(domain)
        test_msg = {"message": "message", "title": "title", "sticky": True}
        self.env.user.notify_success(**test_msg)
        news = bus_bus.search(domain) - existing
        self.assertEqual(1, len(news))
        test_msg.update({"type": SUCCESS})
        payload = json.loads(news.message)["payload"][0]
        self.assertDictEqual(test_msg, payload)

    def test_notify_danger(self):
        bus_bus = self.env["bus.bus"]
        domain = [("channel", "=", self.env.user.notify_danger_channel_name)]
        existing = bus_bus.search(domain)
        test_msg = {"message": "message", "title": "title", "sticky": True}
        self.env.user.notify_danger(**test_msg)
        news = bus_bus.search(domain) - existing
        self.assertEqual(1, len(news))
        test_msg.update({"type": DANGER})
        payload = json.loads(news.message)["payload"][0]
        self.assertDictEqual(test_msg, payload)

    def test_notify_warning(self):
        bus_bus = self.env["bus.bus"]
        domain = [("channel", "=", self.env.user.notify_warning_channel_name)]
        existing = bus_bus.search(domain)
        test_msg = {"message": "message", "title": "title", "sticky": True}
        self.env.user.notify_warning(**test_msg)
        news = bus_bus.search(domain) - existing
        self.assertEqual(1, len(news))
        test_msg.update({"type": WARNING})
        payload = json.loads(news.message)["payload"][0]
        self.assertDictEqual(test_msg, payload)

    def test_notify_info(self):
        bus_bus = self.env["bus.bus"]
        domain = [("channel", "=", self.env.user.notify_info_channel_name)]
        existing = bus_bus.search(domain)
        test_msg = {"message": "message", "title": "title", "sticky": True}
        self.env.user.notify_info(**test_msg)
        news = bus_bus.search(domain) - existing
        self.assertEqual(1, len(news))
        test_msg.update({"type": INFO})
        payload = json.loads(news.message)["payload"][0]
        self.assertDictEqual(test_msg, payload)

    def test_notify_default(self):
        bus_bus = self.env["bus.bus"]
        domain = [("channel", "=", self.env.user.notify_default_channel_name)]
        existing = bus_bus.search(domain)
        test_msg = {"message": "message", "title": "title", "sticky": True}
        self.env.user.notify_default(**test_msg)
        news = bus_bus.search(domain) - existing
        self.assertEqual(1, len(news))
        test_msg.update({"type": DEFAULT})
        payload = json.loads(news.message)["payload"][0]
        self.assertDictEqual(test_msg, payload)

    def test_notify_many(self):
        # check that the notification of a list of users is done with
        # a single call to the bus
        users = self.env.user.search([(1, "=", 1)])

        self.assertTrue(len(users) > 1)
        self.env.user.notify_warning(message="message", target=users.partner_id)

    def test_notify_other_user(self):
        other_user = self.env.ref("base.user_demo")
        other_user_model = self.env["res.users"].with_user(other_user)
        with self.assertRaises(exceptions.UserError):
            other_user_model.browse(self.env.uid).notify_info(message="hello")

    def test_notify_admin_allowed_other_user(self):
        other_user = self.env.ref("base.user_demo")
        other_user.notify_info(message="hello")
