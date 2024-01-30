# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_event_full.tests.common import TestWEventCommon
from odoo.exceptions import ValidationError

class TestTemplateRefModel(TestWEventCommon):

    def test_template_ref_model_constraint(self):

        test_cases = [
            ('mail', 'mail.template', True),
            ('mail', 'sms.template', False),
            ('sms', 'sms.template', True),
            ('sms', 'mail.template', False),
        ]

        for notification_type, template_type, valid in test_cases:
            with self.subTest(notification_type=notification_type, template_type=template_type):
                if template_type == 'mail.template':
                    template = self.env[template_type].create({
                        'name': 'test template',
                        'model_id': self.env['ir.model']._get_id('event.registration'),
                    })
                else:
                    template = self.env[template_type].create({
                        'name': 'test template',
                        'body': 'Body Test',
                        'model_id': self.env['ir.model']._get_id('event.registration'),
                    })
                if not valid:
                    with self.assertRaises(ValidationError) as cm:
                        self.env['event.mail'].create({
                            'event_id': self.event.id,
                            'notification_type': notification_type,
                            'interval_unit': 'now',
                            'interval_type': 'before_event',
                            'template_ref': template,
                        })
                    if notification_type == 'mail':
                        self.assertEqual(str(cm.exception), 'The template which is referenced should be coming from mail.template model.')
                    else:
                        self.assertEqual(str(cm.exception), 'The template which is referenced should be coming from sms.template model.')
