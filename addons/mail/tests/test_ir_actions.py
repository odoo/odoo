# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.base.tests.test_ir_actions import TestServerActionsBase


class TestServerActionsEmail(TestServerActionsBase):

    def test_email_action(self):
        """ Test ir.actions.server email type """
        # create email_template
        email_template = self.env['mail.template'].create({
            'name': 'TestTemplate',
            'email_from': 'myself@example.com',
            'email_to': 'brigitte@example.com',
            'partner_to': '%s' % self.test_partner.id,
            'model_id': self.res_partner_model.id,
            'subject': 'About ${object.name}',
            'body_html': '<p>Dear ${object.name}, your parent is ${object.parent_id and object.parent_id.name or "False"}</p>',
        })
        self.action.write({'state': 'email', 'template_id': email_template.id})
        run_res = self.action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: email server action correctly finished should return False')
        # check an email is waiting for sending
        mail = self.env['mail.mail'].search([('subject', '=', 'About TestingPartner')])
        self.assertEqual(len(mail), 1, 'ir_actions_server: TODO')
        # check email content
        self.assertEqual(mail.body, '<p>Dear TestingPartner, your parent is False</p>',
                         'ir_actions_server: TODO')

    def test_followers_action(self):
        """ Test ir.actions.server email type """
        self.test_partner.message_unsubscribe(self.test_partner.message_partner_ids.ids)
        self.action.write({
            'state': 'followers',
            'partner_ids': [(4, self.env.ref('base.partner_root').id), (4, self.env.ref('base.partner_demo').id)],
            'channel_ids': [(4, self.env.ref('mail.channel_all_employees').id)]
        })
        self.action.with_context(self.context).run()
        self.assertEqual(self.test_partner.message_partner_ids, self.env.ref('base.partner_root') | self.env.ref('base.partner_demo'))
        self.assertEqual(self.test_partner.message_channel_ids, self.env.ref('mail.channel_all_employees'))
