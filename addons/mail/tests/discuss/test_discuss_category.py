# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests import HttpCase


class TestDiscussCategory(MailCommon, HttpCase):
    def setUp(self):
        super().setUp()
        self.channel = self.env["discuss.channel"]._create_channel(group_id=None, name="Test channel")

    def test_assign_channel_categories(self):
        self.authenticate("admin", "admin")
        category_id = self.env["discuss.category"].create({"name": "Services"})

        def get_assign_channel_category_bus():
            return (
                [
                    (self.cr.dbname, "discuss.channel", self.channel.id),
                ],
                [
                    {
                        "type": "mail.record/insert",
                        "payload": {
                            "discuss.category": [
                                {
                                    "id": category_id.id,
                                    "name": category_id.name,
                                    "sequence": category_id.sequence,
                                    "bus_channel_access_token": category_id._get_bus_channel_access_token(),
                                },
                            ],
                            "discuss.channel": [
                                {
                                    "id": self.channel.id,
                                    "discuss_category_id": category_id.id,
                                },
                            ],
                        },
                    },
                ],
            )

        with self.assertBus(get_params=get_assign_channel_category_bus):
            category_id.channel_ids = [(4, self.channel.id)]
