# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

class TestSMSTemplate(TransactionCase):

    def test_sms_template(self):
        partner_id = self.ref("base.res_partner_12")
        template_id = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model'].search([('name', '=', 'res.partner')]).id,
            'body': 'Hello ${object.display_name}'
        })
        content = template_id._render_template(template_id.body, 'res.partner', partner_id)
        self.assertEqual(content, 'Hello Azure Interior')

    def test_sms_dynamic_placeholder(self):
        model_res_partner = self.env['ir.model'].search([('model', '=', 'res.partner')])
        model_res_users = self.env['ir.model'].search([('model', '=', 'res.users')])
        template_id = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': model_res_partner.id,
            'body': 'Hello ${object.display_name}'
        })

        activity_user_id = self.env['ir.model.fields'].search([('model_id', '=', model_res_partner.id), ('name', '=', 'activity_user_id')])
        template_id.model_object_field = activity_user_id.id
        template_id._onchange_dynamic_placeholder()
        self.assertEqual(template_id.sub_object.id, model_res_users.id)

        display_name = self.env['ir.model.fields'].search([('model_id', '=', model_res_users.id), ('name', '=', 'display_name')])
        template_id.sub_model_object_field = display_name.id
        template_id._onchange_dynamic_placeholder()
        self.assertEqual(template_id.copyvalue, '${object.activity_user_id.display_name}')

        active = self.env['ir.model.fields'].search([('model_id', '=', model_res_partner.id), ('name', '=', 'active')])
        template_id.model_object_field = active.id
        template_id._onchange_dynamic_placeholder()
        self.assertFalse(template_id.sub_object)
        self.assertFalse(template_id.sub_model_object_field)
        self.assertEqual(template_id.copyvalue, '${object.active}')

        template_id.null_value = 'test'
        template_id._onchange_dynamic_placeholder()
        self.assertEqual(template_id.copyvalue, "${object.active or '''test'''}")

        template_id.model_object_field = False
        template_id._onchange_dynamic_placeholder()
        self.assertFalse(template_id.copyvalue)

    def test_sms_template_add_context_action(self):
        template_id = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model'].search([('name', '=', 'res.partner')]).id,
            'body': 'Hello ${object.display_name}'
        })
        template_id.create_action()

        # Check template act_window has been updated
        self.assertTrue(bool(template_id.ref_ir_act_window))

        # Check those records
        action_id = template_id.ref_ir_act_window
        self.assertEqual(action_id.name, 'Send SMS Text Message (%s)' % template_id.name)
        self.assertEqual(action_id.binding_model_id.model, template_id.model_id.name)

        # Check the unlink action
        template_id.unlink_action()
        self.assertFalse(bool(template_id.ref_ir_act_window))