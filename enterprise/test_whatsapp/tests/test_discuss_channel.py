# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import escape

from odoo import fields
from odoo.tools.misc import limited_field_access_token
from odoo.addons.test_whatsapp.tests.common import WhatsAppFullCase
from odoo.addons.whatsapp.tests.common import MockIncomingWhatsApp
from odoo.tests import tagged, users


@tagged('wa_message')
class DiscussChannel(WhatsAppFullCase, MockIncomingWhatsApp):

    def test_channel_info_link(self):
        """ Test information posted on channels. Flow

          * a message is sent to the customer;
          * they reply;
          * then another message is posted using a template. This has two
            use cases: either the same user, either another user
          * check record information that should be displayed in channel.
        """
        template = self.whatsapp_template.with_user(self.env.user)
        template_as_admin = self.whatsapp_template.with_user(self.user_wa_admin)
        template_as_emp = self.whatsapp_template.with_user(self.user_employee)
        test_record = self.test_base_record_nopartner.with_env(self.env)

        for reply_template, reply_user, expected_body, error_msg in [
            (
                template_as_admin,
                self.user_wa_admin,
                '<p>Hello World</p>', "Should contain the HTML body of the template sent"
            ), (
                template_as_emp,
                self.user_employee,
                f'<p>A new template was sent on <a target="_blank" '
                f'href="{test_record.get_base_url()}/odoo/{test_record._name}/{test_record.id}">'
                f'{escape(test_record.display_name)}</a>.<br>'
                f'Future replies will be transferred to a new chat.</p>',
                "Should contain channel switch message with related document link"
            ),
        ]:
            with self.subTest(reply_template=template, reply_user=reply_user):
                composer = self._instanciate_wa_composer_from_records(template, test_record)
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()

                with self.mockWhatsappGateway():
                    self._receive_whatsapp_message(self.whatsapp_account, 'Hello', '32499123456')

                composer = self._instanciate_wa_composer_from_records(reply_template, test_record, reply_user)
                with self.mockWhatsappGateway():
                    composer.action_send_whatsapp_template()

                discuss_channel = self.assertWhatsAppDiscussChannel(
                    "32499123456",
                    wa_msg_count=1, msg_count=3,
                    wa_message_fields_values={
                        'state': 'sent',
                    },
                )

                (second_info, answer, first_info) = discuss_channel.message_ids
                self.assertEqual(second_info.body, expected_body, error_msg)
                self.assertEqual(answer.body, '<p>Hello</p>')
                self.assertIn(
                    first_info.body,
                    f'<p>Related WhatsApp Base Test: <a target="_blank" href="{test_record.get_base_url()}/odoo/'
                    f'{test_record._name}/{test_record.id}">{escape(test_record.display_name)}</a></p>',
                    "Should contain a link and display_name to the new record from which the template was sent"
                )
                discuss_channel.sudo().unlink()

    @users('user_wa_admin')
    def test_channel_info_link_noname(self):
        """ Test that a channel can be created for a model without a name field
        and rec_name is correctly used for logged info. """
        test_record_noname = self.env['whatsapp.test.nothread.noname'].create({
            'country_id': self.env.ref('base.be').id,
            'customer_id': self.test_partner.id,
        })
        template = self.whatsapp_template.with_user(self.env.user)
        template.write({
            'model_id': self.env['ir.model']._get_id('whatsapp.test.nothread.noname'),
        })

        composer = self._instanciate_wa_composer_from_records(template, test_record_noname)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(self.whatsapp_account, 'Hello', '32485221100')

        discuss_channel = self.assertWhatsAppDiscussChannel("32485221100", wa_msg_count=1, msg_count=2)
        (answer, first_info) = discuss_channel.message_ids
        self.assertEqual(answer.body, '<p>Hello</p>')
        self.assertIn(
            first_info.body,
            f'<p>Related WhatsApp NoThread / NoResponsible /NoName: <a target="_blank"'
            f' href="{test_record_noname.get_base_url()}/odoo/{test_record_noname._name}/{test_record_noname.id}">'
            f'{escape(test_record_noname.customer_id.name)}</a></p>',
            "Should contain a link and display_name to the new record from which the template was sent")

    @users('user_wa_admin')
    def test_channel_validity_date(self):
        """ Ensure the validity date of a whatsapp channel is only affected by
        messages sent by the whatsapp recipient. """
        template = self.whatsapp_template.with_user(self.env.user)
        test_record = self.test_base_record_nopartner.with_env(self.env)

        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        self._receive_whatsapp_message(self.whatsapp_account, 'Hello', '32499123456')

        discuss_channel = self.env["discuss.channel"].search([("whatsapp_number", "=", "32499123456")])
        self.assertTrue(discuss_channel.whatsapp_channel_valid_until)
        first_valid_date = discuss_channel.whatsapp_channel_valid_until

        composer = self._instanciate_wa_composer_from_records(template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        second_valid_date = discuss_channel.whatsapp_channel_valid_until

        self.assertEqual(first_valid_date, second_valid_date)

    def test_message_reaction(self):
        """Check a reaction is correctly added on a whatsapp message."""
        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(self.whatsapp_account, "test", "32499123456")
        discuss_channel = self.assertWhatsAppDiscussChannel("32499123456", wa_msg_count=1, msg_count=1)
        channel = (self.cr.dbname, "discuss.channel", discuss_channel.id)
        partner = self.env.user.partner_id
        guest = self.env["mail.guest"]
        message = discuss_channel.message_ids[0]
        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account, "", "32499123456",
                additional_message_values={
                    "reaction": {
                        "message_id": message.wa_message_ids[0].msg_uid,
                        "emoji": "😊",
                    },
                    "type": "reaction",
                },
            )
        self._reset_bus()
        with self.assertBus(
            [channel] * 2,
            [{
                "type": "mail.record/insert",
                "payload": {
                    "mail.message": [{
                        "id": message.id,
                        "reactions": [["DELETE", {"message": message.id, "content": "😊"}]],
                    }],
                },
            }, {
                "type": "mail.record/insert",
                "payload": {
                    "MessageReactions": [{
                        "content": "👍",
                        "count": 1,
                        "message": message.id,
                        "personas": [{"id": message.author_id.id, "type": "partner"}],
                        # new reaction, and there is no way that we can get the id of the reaction, so that the sequence is directly +1
                        "sequence": message.reaction_ids.ids[0] + 1,
                    }],
                    "mail.message": [{
                        "id": message.id,
                        "reactions": [["ADD", [{"message": message.id, "content": "👍"}]]],
                    }],
                    "res.partner": [{
                        "avatar_128_access_token": limited_field_access_token(
                            message.author_id, "avatar_128"
                        ),
                        "id": message.author_id.id,
                        "name": "+32499123456",
                        "write_date": fields.Datetime.to_string(
                            message.author_id.write_date
                        ),
                    }],
                },
            }],
        ):
            with self.mockWhatsappGateway():
                self._receive_whatsapp_message(
                    self.whatsapp_account, "", "32499123456",
                    additional_message_values={
                        "reaction": {
                            "message_id": message.wa_message_ids[0].msg_uid,
                            "emoji": "👍",
                        },
                        "type": "reaction",
                    },
                )

        reaction = message.reaction_ids
        self.assertEqual(len(reaction), 1, "One reaction should be present.")
        self.assertEqual(reaction.content, "👍", "The reaction emoji should be 👍.")
        self._reset_bus()
        with self.assertBus(
            [channel] * 3,
            [{
                "type": "mail.record/insert",
                "payload": {
                    "MessageReactions": [{
                        "content": "🚀",
                        "count": 1,
                        "message": message.id,
                        "personas": [{"id": partner.id, "type": "partner"}],
                        "sequence": message.reaction_ids.ids[0] + 1,
                    }],
                    "mail.message": [{
                        "id": message.id,
                        "reactions": [["ADD", [{"message": message.id, "content": "🚀"}]]],
                    }],
                    "res.partner": [{
                        "id": partner.id,
                        "name": partner.name,
                        "write_date": fields.Datetime.to_string(partner.write_date),
                        "avatar_128_access_token": limited_field_access_token(
                            partner, "avatar_128"
                        ),
                    }],
                },
            }, {
                "type": "mail.record/insert",
                "payload": {
                    "mail.message": [{
                        "id": message.id,
                        "reactions": [["DELETE", {"message": message.id, "content": "🚀"}]],
                    }],
                },
            }, {
                "type": "mail.record/insert",
                "payload": {
                    "MessageReactions": [{
                        "content": "🔥",
                        "count": 1,
                        "message": message.id,
                        "personas": [{"id": partner.id, "type": "partner"}],
                        "sequence": message.reaction_ids.ids[0] + 2,
                    }],
                    "mail.message": [{
                        "id": message.id,
                        "reactions": [["ADD", [{"message": message.id, "content": "🔥"}]]],
                    }],
                    "res.partner": [{
                        "id": partner.id,
                        "name": partner.name,
                        "write_date": fields.Datetime.to_string(partner.write_date),
                        "avatar_128_access_token": limited_field_access_token(
                            partner, "avatar_128"
                        ),
                    }],
                },
            }]
        ):
            with self.mockWhatsappGateway():
                # Add first reaction 🚀 (user sent)
                message._message_reaction("🚀", "add", partner, guest)

                # Assert total 2 reactions now (🚀 from Odoo user, 👍 from WA user)
                reactions = message.reaction_ids
                self.assertEqual(len(reactions), 2)
                self.assertSetEqual(set(reactions.mapped("content")), {"🚀", "👍"})

                # Replace 🚀 with 🔥
                message._message_reaction("🔥", "add", partner, guest)

                # Assert reaction still count to 2, and Odoo user reaction is 🔥
                reactions = message.reaction_ids
                self.assertEqual(len(reactions), 2)
                self.assertSetEqual(set(reactions.mapped("content")), {"🔥", "👍"})

                # Try re-adding 🔥 (should not resend API call)
                message._message_reaction("🔥", "add", partner, guest)

            self.assertEqual(len(self._wa_msg_sent_vals), 2, "Two API calls should've been made for two different emojis (🚀 → 🔥).")
            self.assertEqual(self._wa_msg_sent_vals[-1]["emoji"], "🔥", "Last API call should've sent 🔥 as emoji.")
