# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import TestMail

class TestMailActivity(TestMail):

    def test_action_feedback_attachment(self):
        Partner = self.env['res.partner']
        Activity = self.env['mail.activity']
        Attachment = self.env['ir.attachment']
        Message = self.env['mail.message']

        partner = self.env['res.partner'].create({
            'name': 'Tester',
        })

        activity = Activity.create({
            'summary': 'Test',
            'activity_type_id': 1,
            'res_model_id': self.env.ref('base.model_res_partner').id,
            'res_id': partner.id,
        })

        attachments = Attachment
        attachments += Attachment.create({
            'name': 'test',
            'res_name': 'test',
            'res_model': 'mail.activity',
            'res_id': activity.id,
            'datas': 'test',
            'datas_fname': 'test.pdf',
        })
        attachments += Attachment.create({
            'name': 'test2',
            'res_name': 'test',
            'res_model': 'mail.activity',
            'res_id': activity.id,
            'datas': 'testtest',
            'datas_fname': 'test2.pdf',
        })

        # Adding the attachments to the activity
        activity.attachment_ids = attachments

        # Checking if the attachment has been forwarded to the message
        # when marking an activity as "Done"
        activity.action_feedback()
        activity_message = Message.search([], order='id desc', limit=1)
        self.assertEqual(set(activity_message.attachment_ids.ids), set(attachments.ids))
        for attachment in attachments:
            self.assertEqual(attachment.res_id, activity_message.id)
            self.assertEqual(attachment.res_model, activity_message._name)

