# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from freezegun import freeze_time

from odoo.addons.whatsapp.tests.common import WhatsAppCommon
from odoo.tests import tagged


@tagged('wa_message')
class WhatsAppMessage(WhatsAppCommon):

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
