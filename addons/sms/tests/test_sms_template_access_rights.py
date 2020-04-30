# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import new_test_user, users
from odoo.tests import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged('post_install')
class TestSmsTemplateAccessRights(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = new_test_user(cls.env, login='user_admin', groups='base.group_system')
        cls.basic_user = new_test_user(cls.env, login='basic_user', groups='base.group_user')
        sms_enabled_models = cls.env['ir.model'].search([('is_mail_thread_sms', '=', True), ('transient', '=', False)])
        vals = []
        for model in sms_enabled_models:
            vals.append({
                'name': 'SMS Template ' + model.name,
                'body': 'Body Test',
                'model_id': model.id,
            })
        cls.sms_templates = cls.env['sms.template'].create(vals)

    @users('basic_user')
    def test_access_rights_user_sms_template(self):
        # Check if a member of group_user can only read on sms.template
        for sms_template in self.sms_templates.with_user(self.env.user):
            self.assertTrue(bool(sms_template.name))
            with self.assertRaises(AccessError):
                sms_template.write({'name': 'Update Template'})
            with self.assertRaises(AccessError):
                sms_template.unlink()
            with self.assertRaises(AccessError):
                self.env['sms.template'].create({
                    'name': 'New SMS Template ' + sms_template.model_id.name,
                    'body': 'Body Test',
                    'model_id': sms_template.model_id.id,
                })

    @users('user_admin')
    def test_access_rights_manager_sms_template(self):
        # Check if a member of group_system can RUD on sms.template
        for sms_template in self.sms_templates:
            self.assertTrue(bool(sms_template.name))
            sms_template.write({'body': 'New body from admin'})
            sms_template.unlink()
