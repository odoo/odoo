# -*- coding: utf-8 -*-

from openerp.addons.base.tests.test_ir_actions import TestServerActionsBase


class TestServerActionsEmail(TestServerActionsBase):

    def test_00_state_email(self):
        """ Test ir.actions.server email type """
        # create email_template
        email_template = self.env['mail.template'].create({
            'name': 'TestTemplate',
            'email_from': 'myself@example.com',
            'email_to': 'brigitte@example.com',
            'partner_to': '%s' % self.test_partner_id,
            'model_id': self.res_partner_model_id,
            'subject': 'About ${object.name}',
            'body_html': '<p>Dear ${object.name}, your parent is ${object.parent_id and object.parent_id.name or "False"}</p>',
        })
        action = self.env['ir.actions.server'].browse(self.act_id)
        action.write({'state': 'email', 'template_id': email_template.id})
        run_res = action.with_context(self.context).run()
        self.assertFalse(run_res, 'ir_actions_server: email server action correctly finished should return False')
        # check an email is waiting for sending
        mail = self.env['mail.mail'].search([('subject', '=', 'About TestingPartner')])
        self.assertEqual(len(mail.ids), 1, 'ir_actions_server: TODO')
        # check email content
        self.assertEqual(mail.body, '<p>Dear TestingPartner, your parent is False</p>',
                         'ir_actions_server: TODO')
