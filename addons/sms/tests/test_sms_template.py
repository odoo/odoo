# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import SavepointCase, users
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install')
class TestSmsTemplateAccessRights(SavepointCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = mail_new_test_user(cls.env, login='user_system', groups='base.group_system')
        cls.basic_user = mail_new_test_user(cls.env, login='user_employee', groups='base.group_user')
        sms_enabled_models = cls.env['ir.model'].search([('is_mail_thread', '=', True), ('transient', '=', False)])
        vals = []
        for model in sms_enabled_models:
            vals.append({
                'name': 'SMS Template ' + model.name,
                'body': 'Body Test',
                'model_id': model.id,
            })
        cls.sms_templates = cls.env['sms.template'].create(vals)

    @users('user_employee')
    @mute_logger('odoo.models.unlink')
    def test_access_rights_user(self):
        # Check if a member of group_user can only read on sms.template
        for sms_template in self.env['sms.template'].browse(self.sms_templates.ids):
            self.assertTrue(bool(sms_template.name))
            with self.assertRaises(AccessError):
                sms_template.write({'name': 'Update Template'})
            with self.assertRaises(AccessError):
                self.env['sms.template'].create({
                    'name': 'New SMS Template ' + sms_template.model_id.name,
                    'body': 'Body Test',
                    'model_id': sms_template.model_id.id,
                })
            with self.assertRaises(AccessError):
                sms_template.unlink()

    @users('user_system')
    @mute_logger('odoo.models.unlink', 'odoo.addons.base.models.ir_model')
    def test_access_rights_system(self):
        admin = self.env.ref('base.user_admin')
        for sms_template in self.env['sms.template'].browse(self.sms_templates.ids):
            self.assertTrue(bool(sms_template.name))
            sms_template.write({'body': 'New body from admin'})
            self.env['sms.template'].create({
                'name': 'New SMS Template ' + sms_template.model_id.name,
                'body': 'Body Test',
                'model_id': sms_template.model_id.id,
            })

            # check admin is allowed to read all templates since he can be a member of
            # other groups applying restrictions based on the model
            self.assertTrue(bool(self.env['sms.template'].with_user(admin).browse(sms_template.ids).name))

            sms_template.unlink()
