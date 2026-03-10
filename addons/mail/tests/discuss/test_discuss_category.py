# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCase
from odoo.tests import HttpCase


class TestDiscussCategory(MailCase, HttpCase):

    def test_assign_channel_categories(self):
        self.authenticate("admin", "admin")
        channel = self.env["discuss.channel"]._create_channel(group_id=None, name="Public Channel")
        category_id = self.env["discuss.category"].create({"name": "Services"})

        def get_assign_channel_category_bus():
            return (
                [channel],
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
                                    "id": channel.id,
                                    "discuss_category_id": category_id.id,
                                },
                            ],
                        },
                    },
                ],
            )

        with self.assertBus(get_params=get_assign_channel_category_bus):
            category_id.channel_ids = [(4, channel.id)]
