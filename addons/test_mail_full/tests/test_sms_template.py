# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon, TestMailFullRecipients


class TestSmsTemplate(TestMailFullCommon, TestMailFullRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSmsTemplate, cls).setUpClass()
        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)

        cls.body_en = 'Dear {{ object.display_name }} this is an SMS.'
        cls.body_fr = u"Hello {{ object.display_name }} ceci est en français."
        cls.sms_template = cls._create_sms_template('mail.test.sms', body=cls.body_en)

    def test_sms_template_render(self):
        rendered_body = self.sms_template._render_template(self.sms_template.body, self.sms_template.model, self.test_record.ids)
        self.assertEqual(rendered_body[self.test_record.id], 'Dear %s this is an SMS.' % self.test_record.display_name)

        rendered_body = self.sms_template._render_field('body', self.test_record.ids)
        self.assertEqual(rendered_body[self.test_record.id], 'Dear %s this is an SMS.' % self.test_record.display_name)

    def test_sms_template_lang(self):
        self.env['res.lang']._activate_lang('fr_FR')
        self.user_admin.write({'lang': 'en_US'})
        self.env['ir.translation'].create({
            'type': 'model',
            'name': 'sms.template,body',
            'lang': 'fr_FR',
            'res_id': self.sms_template.id,
            'src': self.sms_template.body,
            'value': self.body_fr,
        })
        # set template to try to use customer lang
        self.sms_template.write({
            'lang': '{{ object.customer_id.lang }}',
        })
        # create a second record linked to a customer in another language
        self.partner_2.write({
            'lang': 'fr_FR',
        })
        test_record_2 = self.env['mail.test.sms'].create({
            'name': 'Test',
            'customer_id': self.partner_2.id,
        })

        self.assertEqual(self.sms_template.body, self.body_en)
        self.assertEqual(self.sms_template.with_context(lang='fr_FR').body, self.body_fr)

        rid_to_lang = self.sms_template._render_lang((self.test_record | test_record_2).ids)
        self.assertEqual(set(rid_to_lang.keys()), set((self.test_record | test_record_2).ids))
        for rid, lang in rid_to_lang.items():
            # TDE FIXME: False or en_US ?
            if rid == self.test_record.id:
                self.assertEqual(lang, 'en_US')
            elif rid == test_record_2.id:
                self.assertEqual(lang, 'fr_FR')
            else:
                self.assertTrue(False)

        tpl_to_rids = self.sms_template._classify_per_lang((self.test_record | test_record_2).ids)
        for lang, (tpl, rids) in tpl_to_rids.items():
            # TDE FIXME: False or en_US ?
            if lang == 'en_US':
                self.assertEqual(rids, self.test_record.ids)
            elif lang == 'fr_FR':
                self.assertEqual(rids, test_record_2.ids)
            else:
                self.assertTrue(False, 'Should not return lang %s' % lang)

    def test_sms_template_create_and_unlink_sidebar_action(self):
        ActWindow = self.env['ir.actions.act_window']
        self.sms_template.action_create_sidebar_action()
        action_id = self.sms_template.sidebar_action_id.id

        self.assertNotEqual(action_id, False)
        self.assertEqual(ActWindow.search_count([('id', '=', action_id)]), 1)

        self.sms_template.action_unlink_sidebar_action()
        self.assertEqual(ActWindow.search_count([('id', '=', action_id)]), 0)

    def test_sms_template_unlink_with_action(self):
        ActWindow = self.env['ir.actions.act_window']
        self.sms_template.action_create_sidebar_action()
        action_id = self.sms_template.sidebar_action_id.id

        self.sms_template.unlink()
        self.assertEqual(ActWindow.search_count([('id', '=', action_id)]), 0)
