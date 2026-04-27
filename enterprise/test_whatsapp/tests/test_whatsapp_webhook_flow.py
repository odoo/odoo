# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.controllers.thread import ThreadController
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.test_whatsapp.tests.common import WhatsAppFullCase
from odoo.addons.website.tools import MockRequest
from odoo.addons.whatsapp.tests.common import MockIncomingWhatsApp
from odoo.tests import tagged, users


@tagged('whatsapp', 'post_install', '-at_install', 'wa_webhook')
class WhatsAppWebhookCase(WhatsAppFullCase, MockIncomingWhatsApp):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_salesperson = mail_new_test_user(
            cls.env,
            groups="base.group_user",
            login="user_salesperson",
        )

        cls.user_salesperson_2 = mail_new_test_user(
            cls.env,
            groups="base.group_user",
            login="user_salesperson_2",
        )

        cls.user_salesperson_3 = mail_new_test_user(
            cls.env,
            groups="base.group_user",
            login="user_salesperson_3",
        )

    @users('user_wa_admin')
    def test_blocklist_message(self):
        """ Test the automatic blocklist mechanism when receiving 'stop'. """
        MailThreadController = ThreadController()
        test_record = self.test_base_record_nopartner.with_env(self.env)
        whatsapp_template = self.whatsapp_template.with_env(self.env)

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account,
                "Hello, how can remove my number from your WhatsApp listing?",
                "32499123456",
            )
        discuss_channel = self.assertWhatsAppDiscussChannel(
            "32499123456", wa_account=self.whatsapp_account,
            wa_message_fields_values={
                'state': 'received',
            },
        )

        with self.mockWhatsappGateway():
            discuss_channel.message_post(
                body="Hello, you can just send 'stop' to this number.",
                message_type="whatsapp_message",
            )

        discuss_channel = self.assertWhatsAppDiscussChannel(
            "32499123456", wa_account=self.whatsapp_account,
            wa_msg_count=2, msg_count=2,
            wa_message_fields_values={
                'state': 'sent',
            },
        )

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(self.whatsapp_account, "Stop", "32499123456")
        # at this point, we should have 3 mail.messages and whatsapp.messages
        discuss_channel = self.assertWhatsAppDiscussChannel(
            "32499123456", wa_account=self.whatsapp_account,
            wa_msg_count=3, msg_count=3,
            wa_message_fields_values={
                'state': 'received',
            },
        )

        # make sure we have a matching entry in the blacklist table
        blacklist_record = self.env["phone.blacklist"].sudo().with_context(active_test=False).search([
            ("number", "=", "+32499123456"),
            ("active", "=", True),
        ])
        self.assertTrue(bool(blacklist_record))

        # post a regular message: should not send through WhatsApp
        with self.mockWhatsappGateway(), MockRequest(self.env):
            data = MailThreadController.mail_message_post(
                'discuss.channel', discuss_channel.id,
                {
                    'body': 'Hello, Did it work?',
                    'message_type': 'whatsapp_message'
                }
            )
            not_sent_message = self.env["mail.message"].browse(data["mail.message"][0]["id"])
        self.assertWAMessage("error", fields_values={
            "failure_type": "blacklisted",
            "mail_message_id": not_sent_message,
            "mobile_number": "+32499123456",
        })

        # attempt to send a template: should not send through WhatsApp
        composer = self._instanciate_wa_composer_from_records(whatsapp_template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        self.assertWAMessage("error", fields_values={
            "failure_type": "blacklisted",
            "mobile_number": "+32499123456",
        })

        # remove from blacklist, make sure we can send WhatsApp messages again
        self._receive_whatsapp_message(
            self.whatsapp_account,
            "Hello, I would like to receive messages again.",
            "32499123456",
        )
        # should be unblacklisted
        blacklist_record = self.env["phone.blacklist"].sudo().with_context(active_test=False).search([
            ("number", "=", "+32499123456")
        ])
        self.assertEqual(len(blacklist_record), 1)
        self.assertEqual(blacklist_record.active, False)

        with self.mockWhatsappGateway(), MockRequest(self.env):
            data = MailThreadController.mail_message_post(
                'discuss.channel', discuss_channel.id,
                {
                    'body': 'Welcome back!',
                    'message_type': 'whatsapp_message',
                },
            )
            sent_message = self.env["mail.message"].browse(data["mail.message"][0]["id"])
        self.assertWAMessage("sent", fields_values={
            "failure_type": False,
            "mail_message_id": sent_message,
            "mobile_number": "+32499123456",
        })

    @users('user_wa_admin')
    def test_conversation_match(self):
        """ Test a conversation with multiple channels and messages. Received
        messages should all be linked to the document if there is a suitable
        message sent within the 15 days time frame (see '_find_active_channel').
        If we send a message in reply to a specific one, we should find the
        discuss message of that channel and use that channel instead. """
        test_record = self.test_base_record_nopartner.with_env(self.env)
        whatsapp_template = self.whatsapp_template.with_env(self.env)

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(self.whatsapp_account, "Hey there", "32499123456")
        no_document_discuss_channel = self.assertWhatsAppDiscussChannel(
            "32499123456",
        )

        with self.mockWhatsappGateway():
            operator_message = no_document_discuss_channel.message_post(
                body="Hello, feel free to ask any questions you may have!",
                message_type="whatsapp_message"
            )
        self.assertEqual(len(no_document_discuss_channel.message_ids), 2)
        self.assertWAMessage(
            "sent",
            fields_values={
                "mail_message_id": operator_message,
            },
        )

        # send using template -> replies will be associated to existing active
        # channel of customer, not linked to a new channel as before 17.4
        composer = self._instanciate_wa_composer_from_records(whatsapp_template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()
        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account, "Hello, why are you sending me this?", "32499123456",
            )

        # message should be correctly associated to existing discuss conversation
        document_discuss_channel = self.assertWhatsAppDiscussChannel(
            "32499123456",
            channel_domain=[("id", "=", no_document_discuss_channel.id)],
            msg_count=4,
            wa_msg_count=3,
        )

        with self.mockWhatsappGateway():
            document_discuss_channel.message_post(
                body="Hello, sorry it was a mistake.",
                message_type="whatsapp_message")

        self.assertEqual(len(document_discuss_channel.message_ids), 5)

    @users('admin')
    def test_conversation_match_multi_user(self):
        """Test a conversation with multiple users and models. All the templates
        related conversations initiated by a user should be associated to a
        single channel. If another user starts a new conversation using template
        it should be associated to a new channel."""
        test_record_1 = self.test_base_record_nopartner.with_env(self.env)
        test_record_2 = self.env['whatsapp.test.nothread'].create({
            "name": "Test Record 2",
            "phone": "+32 499 12 34 56",  # same number as test_record_1 but formatted differently
        })
        whatsapp_template_1 = self.whatsapp_template.with_env(self.env)
        whatsapp_template_2 = whatsapp_template_1.copy({
            "model_id": self.env["ir.model"]._get_id("whatsapp.test.nothread"),
            "name": "No Responsible Template",
            "status": "approved",
            "template_name": "no_responsible_template",
        })

        # send first template + answer
        discuss_channel = self.simulate_conversation(
            whatsapp_template_1, test_record_1, "32499123456",
            exp_msg_count=2, exp_wa_msg_count=1,
        )
        template_1_wa_msg = self._new_wa_msg

        # sending template of different model with first user should be linked
        # to same channel
        self.simulate_conversation(
            whatsapp_template_2, test_record_2, "32499123456",
            exp_channel_domain=[("id", "=", discuss_channel.id)],
            exp_msg_count=4, exp_wa_msg_count=2,
        )

        # receive a message as a reply to whatsapp_template_1 message should be
        # properly linked in same channel
        self.simulate_conversation(
            False, test_record_1, "32499123456",
            exp_channel_domain=[("id", "=", discuss_channel.id)],
            exp_msg_count=5, exp_wa_msg_count=3,
            receive_message_values={"context": {"id": template_1_wa_msg.msg_uid}}
        )

        # another user sends template -> new channel
        new_discuss_channel = self.simulate_conversation(
            whatsapp_template_1, test_record_1, "32499123456",
            template_with_user=self.user_salesperson_2,
            exp_channel_domain=[("id", "!=", discuss_channel.id)],
            exp_msg_count=2, exp_wa_msg_count=1,
        )

        # receive a message as a reply to whatsapp_template_1 message should be
        # properly linked in first channel even if another channel exists with
        # the customer
        self.simulate_conversation(
            False, test_record_1, "32499123456",
            exp_channel_domain=[("id", "=", discuss_channel.id)],
            exp_msg_count=7, exp_wa_msg_count=4,
            receive_message_values={"context": {"id": template_1_wa_msg.msg_uid}}
        )

        # sending template with first user should be associated to new channel
        new_discuss_channel = self.simulate_conversation(
            whatsapp_template_1, test_record_1, "32499123456",
            exp_channel_domain=[("id", "not in", [discuss_channel.id, new_discuss_channel.id])],
            exp_msg_count=2, exp_wa_msg_count=1,
        )

    @users('user_wa_admin')
    def test_conversation_match_multi_account(self):
        """When there are 2 business accounts configured with different numbers

          * if account 1 receives a message from a number then it should create
            a channel with the 1st account;
          * if account 2 receives a message from the same number then it should
            create a new, not reuse the one from first account;
        """
        test_record = self.test_base_record_nopartner.with_env(self.env)
        whatsapp_template = self.whatsapp_template.with_env(self.env)

        composer = self._instanciate_wa_composer_from_records(whatsapp_template, test_record)
        with self.mockWhatsappGateway():
            composer.action_send_whatsapp_template()

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account, "Hello,can you help me?", "32499123456",
            )
        channel_1 = self.assertWhatsAppDiscussChannel(
            "32499123456", wa_account=self.whatsapp_account,
            msg_count=2,
        )

        # Receive a message from the same number but for the 2nd account
        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account_2, "Hello,can you help me?", "32499123456",
            )
        channel_2 = self.assertWhatsAppDiscussChannel(
            "32499123456", wa_account=self.whatsapp_account_2,
            msg_count=1,
        )
        self.assertNotEqual(channel_1, channel_2)
        self.assertEqual(len(channel_1.message_ids), 2)

    @users('user_wa_admin')
    def test_conversation_match_multi_account_same_waba(self):
        """ Test receiving messages when multiple accounts share the same account_uid.
        The signature check should pass and messages should be routed to the correct account
        based on the phone_uid.
        """
        account_3 = self.whatsapp_account.sudo().copy({
            'phone_uid': '9876543210',
        })

        accounts = self.env['whatsapp.account'].sudo().search([('account_uid', '=', self.whatsapp_account.account_uid)])
        self.assertEqual(len(accounts), 2)

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account, "Message for Account 1", "32499123456",
            )
        channel_1 = self.assertWhatsAppDiscussChannel(
            "32499123456", wa_account=self.whatsapp_account,
        )

        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                account_3, "Message for Account 3", "32499123456",
            )
        channel_3 = self.assertWhatsAppDiscussChannel(
            "32499123456", wa_account=account_3,
        )
        self.assertNotEqual(channel_1, channel_3)

    def test_receive_no_document(self):
        """ Receive a message that is not linked to any document. It should
        create a 'standalone' channel with the whatsapp account notified people
        and create a new customer. """
        existing_partners = self.env['res.partner'].search([])
        with self.mockWhatsappGateway():
            self._receive_whatsapp_message(
                self.whatsapp_account, "Hello, I have a question please.", "32499123456"
            )
        discuss_channel = self.assertWhatsAppDiscussChannel(
            "32499123456",
            wa_mail_message_values={
                'body': '<p>Hello, I have a question please.</p>',
            },
        )
        new_partner = self.env['res.partner'].search([('id', 'not in', existing_partners.ids)])
        self.assertEqual(len(new_partner), 1)
        self.assertEqual(discuss_channel.channel_partner_ids, self.user_wa_admin.partner_id + new_partner)
        self.assertEqual(new_partner.mobile, "+32499123456")
        self.assertEqual(new_partner.name, "+32499123456")
        self.assertFalse(new_partner.phone)

    def test_responsible_with_template(self):
        """ Test various use cases of receiving a message that is linked to a
        template. Main idea is to check who is added to notified people. """
        test_template = self.whatsapp_template.copy()
        test_template.write({
            'model_id': self.env['ir.model']._get_id('whatsapp.test.responsible'),
            'name': 'Responsible Template',
            'template_name': 'responsible_template',
            'status': 'approved',
        })
        test_template_no_record = test_template.copy()
        test_template_no_record.write({
            'model_id': self.env['ir.model']._get_id('whatsapp.test.nothread'),
            'name': 'No Responsible Template',
            'template_name': 'no_responsible_template',
            'status': 'approved',
        })

        test_record = self.env['whatsapp.test.responsible'].create({
            'name': 'Test Record',
            'phone': '+32 497 99 99 99',
        })
        test_record_no_responsible = self.env['whatsapp.test.nothread'].create({
            'name': 'Test Record No Responsible',
            'phone': '+32 497 11 11 11',
        })

        expected_responsible = self.user_wa_admin
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record was created/written on by superuser
            # there is no method to get a responsible
            # -> should be the last fallback: 'account.notify_user_ids'
            self._test_responsible_with_template(
                test_record_no_responsible,
                '+32497111111',
                expected_responsible,
                test_template_no_record)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_wa_admin
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record was created/written on by superuser
            # -> should be the last fallback: 'account.notify_user_ids'
            self._test_responsible_with_template(
                test_record,
                '+32497999999',
                expected_responsible,
                test_template)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        test_record.with_user(self.user_salesperson).write({'name': 'Edited name'})
        expected_responsible = self.user_salesperson
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record was written on by user_salesperson
            # -> should be the write_uid fallback: 'user_salesperson'
            self._test_responsible_with_template(
                test_record,
                '+32497999999',
                expected_responsible,
                test_template)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_salesperson_2
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by user_salesperson_2
            # -> should be the author fallback: 'user_salesperson_2'
            self._test_responsible_with_template(
                test_record,
                '+32497999999',
                expected_responsible,
                test_template,
                context_user=self.user_salesperson_2)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_salesperson_3
        test_record.write({'user_id': self.user_salesperson_3.id})
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by superuser (e.g: automated process)
            # record is owned by user_salesperson_3
            # -> should be the owner (user_id) fallback: 'user_salesperson_3'
            self._test_responsible_with_template(
                test_record,
                '+32497999999',
                expected_responsible,
                test_template)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels

        expected_responsible = self.user_salesperson_2 | self.user_salesperson_3
        test_record.write({'user_id': self.user_salesperson_3.id})
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by user_salesperson_2
            # record is owned by user_salesperson_3
            # -> should be the owner (user_id) + sender: 'user_salesperson_2' + 'user_salesperson_3'
            self._test_responsible_with_template(
                test_record,
                '+32497999999',
                expected_responsible,
                test_template,
                context_user=self.user_salesperson_2)
        self.env['discuss.channel'].search([('channel_type', '=', 'whatsapp')]).unlink()  # reset channels
        test_record.user_id = False  # reset responsible user

        expected_responsible = self.user_salesperson | self.user_salesperson_2 | self.user_salesperson_3
        test_record.write({'user_ids': (self.user_salesperson | self.user_salesperson_3).ids})
        with self.subTest(expected_responsible=expected_responsible):
            # template is sent by user_salesperson_2
            # record is owned by user_salesperson AND user_salesperson_3
            # -> should be the owners (user_ids) + sender:
            # 'user_salesperson' + 'user_salesperson_2' + 'user_salesperson_3'
            self._test_responsible_with_template(
                test_record,
                '+32497999999',
                expected_responsible,
                test_template,
                context_user=self.user_salesperson_2)

    def _test_responsible_with_template(self, test_record, exp_phone, expected_responsible, template_id, context_user=False):
        """ Receive a message that is linked to a template sent on test_record.
        Should create a channel linked to that document, using the 'expected_responsible'
        as members. """
        # assumes valid phone numbers with country code
        customer_phone_number = test_record.phone.lstrip('+').replace(' ', '')

        with self.mockWhatsappGateway():
            composer = self._instanciate_wa_composer_from_records(template_id, test_record, with_user=context_user)
            composer._send_whatsapp_template()

            self._receive_whatsapp_message(
                self.whatsapp_account,
                "Hello, I have already paid this.",
                customer_phone_number,
            )

        discuss_channel = self.env["discuss.channel"].search([
            ("whatsapp_number", "=", customer_phone_number)])
        self.assertTrue(bool(discuss_channel))
        self.assertEqual(len(discuss_channel.message_ids), 2)
        channel_messages = discuss_channel.message_ids.sorted(lambda message: message.id)
        context_message = channel_messages[0]
        self.assertIn(f"Related {self.env['ir.model']._get(test_record._name).display_name}:", context_message.body)
        self.assertIn(test_record.name, context_message.body)
        self.assertIn(f"/odoo/{test_record._name}/{test_record.id}", context_message.body,
                      "Should contain a link to the context record")

        customer_message = channel_messages[1]
        self.assertEqual(customer_message.body, "<p>Hello, I have already paid this.</p>")

        for user in expected_responsible:
            self.assertIn(user.partner_id, discuss_channel.channel_partner_ids)
        customer_partner = discuss_channel.channel_partner_ids - expected_responsible.partner_id
        self.assertEqual(len(customer_partner), 1)
        self.assertEqual(customer_partner.name, exp_phone)
