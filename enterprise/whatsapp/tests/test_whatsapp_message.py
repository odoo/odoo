# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.addons.whatsapp.tests.common import MockIncomingWhatsApp, WhatsAppCommon
from odoo.tests import tagged


@tagged('wa_message')
class WhatsAppMessage(WhatsAppCommon, MockIncomingWhatsApp):

    @freeze_time('2023-08-20')
    def test_gc_whatsapp_messages(self):
        messages = self.env['whatsapp.message'].create([{
             'body': 'Old Sent Message',
             'create_date': datetime(2023, 8, 1),
             'state': 'sent',
         }, {
             'body': 'Old Received Message',
             'create_date': datetime(2023, 6, 2),
             'state': 'received',
         }, {
             'body': 'Old Failed Message',
             'create_date': datetime(2023, 5, 15),
             'state': 'error',
         }, {
             'body': 'Old Queued Message',
             'create_date': datetime(2023, 4, 7),
             'state': 'outgoing',
         }, {
             'body': 'Recent Sent Message',
             'create_date': datetime(2023, 8, 7),
             'state': 'sent',
         }, {
             'body': 'Recent Received Message',
             'create_date': datetime(2023, 8, 12),
             'state': 'received',
         }, {
             'body': 'Recent Failed Message',
             'create_date': datetime(2023, 8, 19),
             'state': 'error',
         }])
        [_old_sent_message, _old_received_message, old_failed_message, old_queued_message,
         recent_sent_message, recent_received_message, recent_failed_message] = messages

        all_messages = self.env['whatsapp.message'].search([('id', 'in', messages.ids)])
        self.assertEqual(set(all_messages.ids), set(messages.ids))
        self.env['whatsapp.message']._gc_whatsapp_messages()
        all_messages = self.env['whatsapp.message'].search([('id', 'in', messages.ids)])
        self.assertEqual(
            set(all_messages.ids),
            set((old_failed_message + old_queued_message + recent_sent_message +
             recent_received_message + recent_failed_message).ids)
        )

    def test_resend_message(self):
        """Check that messages are effectively resent, and only when it makes sense.

        i.e. Only messages that are not unrecoverable and on channels that are still active.
        """
        self._receive_whatsapp_message(self.whatsapp_account, 'Hello', '32499000000')
        with self.mock_datetime_and_now(datetime(2000, 1, 1)):
            self._receive_whatsapp_message(self.whatsapp_account, 'Hello', '32499000001')
        valid_channel = self._find_discuss_channel('32499000000')
        invalid_channel = self._find_discuss_channel('32499000001')
        case_names = [
            'Unrecoverable Message',
            'Recoverable Message',
            'Recoverable Message Outdated Channel',
            'Unknown Error Message',
            'Success Message',
            'Template Body Unrecoverable',
            'Template Body Recoverable',
        ]
        expected_states = ['error', 'sent', 'cancel', 'sent', 'sent', 'error', 'sent']
        expected_failure_types = ['whatsapp_unrecoverable', False, 'outdated_channel', False, False, 'whatsapp_unrecoverable', False]
        valid_channel_message_vals = {
            'model': valid_channel._name,
            'res_id': valid_channel.id,
        }
        invalid_channel_message_vals = {
            'model': invalid_channel._name,
            'res_id': invalid_channel.id,
        }
        customer_record_message_vals = {
            'model': self.whatsapp_customer._name,
            'res_id': self.whatsapp_customer.id,
        }
        mail_messages = self.env['mail.message'].create([
            message_vals | {'body': case_name}
            for message_vals, case_name in zip([
                valid_channel_message_vals,
                valid_channel_message_vals,
                invalid_channel_message_vals,
                valid_channel_message_vals,
                valid_channel_message_vals,
                customer_record_message_vals,
                customer_record_message_vals,
            ], case_names)
        ])
        base_whatsapp_message_vals = {
                'create_date': datetime(2023, 8, 1),
                'mobile_number': valid_channel.whatsapp_number,
                'mobile_number_formatted': valid_channel.whatsapp_number,
                'state': 'error',
                'wa_account_id': self.whatsapp_account.id,
        }
        whatsapp_messages = self.env['whatsapp.message'].create([
            base_whatsapp_message_vals | vals | {'mail_message_id': mail_message.id} for vals, mail_message in zip((
            {
                'failure_type': 'whatsapp_unrecoverable',  # not resent
            },
            {
                'failure_type': 'whatsapp_recoverable',
            },
            {
                'failure_type': 'whatsapp_recoverable',  # not resent, invalid channel
            },
            {
                'failure_type': 'unknown',  # unknown error is resent
            },
            {
                'state': 'sent',  # success message is not resent
            },
            {
                'failure_type': 'whatsapp_unrecoverable',  # not resent
                'wa_template_id': self.simple_whatsapp_template.id,
                'free_text_json': {'free_text_1': 'Template with Unrecoverable Error'}
            },
            {
                'failure_type': 'whatsapp_recoverable',  # resent
                'wa_template_id': self.simple_whatsapp_template.id,
                'free_text_json': {'free_text_1': 'Template with Recoverable Error'}
            },
        ), mail_messages)])
        for whatsapp_message, mail_message in zip(whatsapp_messages, mail_messages):
            mail_message.body = whatsapp_message.body
        with self.mockWhatsappGateway(), self.patchWhatsappCronTrigger():
            whatsapp_messages._resend_failed()

        self.assertListEqual(whatsapp_messages.mapped('state'), expected_states, (
            'Expected 3 newly sent, one existing sent, 1 unrecoverable template error'
            ', 1 unrecoverable direct message, 1 cancel from outdated channel'
        ))
        self.assertListEqual(whatsapp_messages.mapped('failure_type'), expected_failure_types,
            'Messages on outdated channels should be force-cancelled'
        )
        self.assertEqual(len(self._wa_msg_sent_vals), 3, 'Should have resent 2 discuss messages and 1 template')
