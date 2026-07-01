# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.sms.tests.common import SMSCommon


class TestSmsSms(SMSCommon):

    def test_process_queue_multi_company(self):
        """Check that SMS for records of multiple companies can be sent in a single cron batch."""
        company_a = self.env.company
        company_b = self.env['res.company'].create({'name': 'Test Company B'})

        msg_a, msg_b = self.env['mail.message'].create([
            {
                'message_type': 'comment',
                'body': 'Message for company A',
                'record_company_id': company_a.id,
            }, {
                'message_type': 'comment',
                'body': 'Message for company B',
                'record_company_id': company_b.id,
            },
        ])

        sms_records = self.env['sms.sms'].create([
            {
                'number': '+32456000001',
                'body': 'SMS A',
                'mail_message_id': msg_a.id,
            },
            {
                'number': '+32456000002',
                'body': 'SMS B',
                'mail_message_id': msg_b.id,
            },
        ])
        self.assertNotEqual(
            sms_records[0].mail_message_id.record_company_id,
            sms_records[1].mail_message_id.record_company_id,
            "The two SMS should belong to different companies",
        )
        self.assertRecordValues(sms_records, [{'state': 'outgoing'}, {'state': 'outgoing'}])

        with self.mockSMSGateway(), \
                patch.object(self.registry['ir.cron'], '_commit_progress'):
            self.env['sms.sms']._process_queue()

        self.assertRecordValues(sms_records, [{'state': 'pending'}, {'state': 'pending'}])
