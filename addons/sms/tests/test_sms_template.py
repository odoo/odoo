# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, users
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('post_install')
class TestSmsTemplateAccessRights(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_admin = mail_new_test_user(cls.env, login='user_system', groups='base.group_user,base.group_system')
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

        cls.sms_dynamic_template = cls.env['sms.template'].sudo().create({
            'body': '{{ object.name }}',
            'model_id': cls.env['ir.model'].sudo().search([('model', '=', 'res.partner')]).id,
        })

        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner'})

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

    @users('user_employee')
    def test_sms_template_rendering_restricted(self):
        self.env['ir.config_parameter'].sudo().set_param('mail.restrict.template.rendering', True)
        self.basic_user.groups_id -= self.env.ref('mail.group_mail_template_editor')

        sms_composer = self.env['sms.composer'].create({
            'composition_mode': 'comment',
            'template_id': self.sms_dynamic_template.id,
            'res_id': self.partner.id,
            'res_model': 'res.partner',
        })

        self.assertEqual(sms_composer.body, self.partner.name, 'Simple user should be able to render SMS template')

        sms_composer.composition_mode = 'mass'
        self.assertEqual(sms_composer.body, '{{ object.name }}', 'In mass mode, we should not render the template')

        body = sms_composer._prepare_body_values(self.partner)[self.partner.id]
        self.assertEqual(body, self.partner.name, 'In mass mode, if the user did not change the body, he should be able to render it')

        sms_composer.body = 'New body: {{ 4 + 9 }}'
        with self.assertRaises(AccessError, msg='User should not be able to write new inline_template code'):
            sms_composer._prepare_body_values(self.partner)

    @users('user_system')
    def test_sms_template_rendering_unrestricted(self):
        self.env['ir.config_parameter'].sudo().set_param('mail.restrict.template.rendering', True)

        sms_composer = self.env['sms.composer'].create({
            'composition_mode': 'comment',
            'template_id': self.sms_dynamic_template.id,
            'res_id': self.partner.id,
            'res_model': 'res.partner',
        })

        body = sms_composer._prepare_body_values(self.partner)[self.partner.id]
        self.assertIn(self.partner.name, body, 'Template Editor should be able to write new Jinja code')
