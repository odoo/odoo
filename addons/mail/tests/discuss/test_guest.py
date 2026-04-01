from odoo import fields
from odoo.addons.mail.tests.common import MailCase
from odoo.tests.common import tagged


@tagged("post_install", "-at_install")
class TestGuest(MailCase):

    def test_updating_guest_name_linked_to_multiple_channels(self):
        """This test ensures that when a guest is linked to multiple channels,
        the guest's name is updated correctly and the appropriate bus notifications are sent.
        """
        guest = self.env['mail.guest'].create({'name': 'Guest'})
        channel_1 = self.env["discuss.channel"]._create_channel(name="Channel 1", group_id=None)
        channel_2 = self.env["discuss.channel"]._create_channel(name="Channel 2", group_id=None)
        channel_1._add_members(guests=guest)
        channel_2._add_members(guests=guest)

        def get_guest_bus_params():
            guest_write_date = fields.Datetime.to_string(guest.write_date)
            message = {
                "type": "mail.record/insert",
                "payload": {
                    "mail.guest": [
                        {
                            "avatar_128_access_token": guest._get_avatar_128_access_token(),
                            "id": guest.id,
                            "name": "Guest Name Updated",
                            "write_date": guest_write_date,
                        },
                    ],
                },
            }

            return (
                [
                    (self.cr.dbname, "discuss.channel", channel_1.id),
                    (self.cr.dbname, "discuss.channel", channel_2.id),
                    (self.cr.dbname, "mail.guest", guest.id),
                ],
                [message, message, message],
            )

        self._reset_bus()
        with self.assertBus(get_params=get_guest_bus_params):
            guest._update_name("Guest Name Updated")
        self.assertEqual(guest.name, "Guest Name Updated")
