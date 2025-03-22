# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
from lxml import etree

from odoo import fields, Command
from odoo.addons.survey.tests import common
from odoo.addons.test_mail.tests.common import MailCommon
from odoo.exceptions import UserError
from odoo.tests import Form
from odoo.tests.common import users


class TestSurveyInvite(common.TestSurveyCommon, MailCommon):

    def setUp(self):
        res = super(TestSurveyInvite, self).setUp()
        # by default signup not allowed
        self.env["ir.config_parameter"].set_param('auth_signup.invitation_scope', 'b2b')
        view = self.env.ref('survey.survey_invite_view_form').sudo()
        tree = etree.fromstring(view.arch)
        # Remove the invisible on `emails` to be able to test the onchange `_onchange_emails`
        # which raises an error when attempting to change `emails`
        # while the survey is set with `users_login_required` to True
        # By default, `<field name="emails"/>` is invisible when `survey_users_login_required` is True,
        # making it normally impossible to change by the user in the web client by default.
        # For tests `test_survey_invite_authentication_nosignup` and `test_survey_invite_token_internal`
        tree.xpath('//field[@name="emails"]')[0].attrib.pop('attrs')
        view.arch = etree.tostring(tree)
        return res

    @users('survey_manager')
    def test_survey_invite_action(self):
        # Check correctly configured survey returns an invite wizard action
        action = self.survey.action_send_survey()
        self.assertEqual(action['res_model'], 'survey.invite')

        # Bad cases
        surveys = [
            # no page
            self.env['survey.survey'].create({'title': 'Test survey'}),
            # no questions
            self.env['survey.survey'].create({'title': 'Test survey', 'question_and_page_ids': [(0, 0, {'is_page': True, 'question_type': False, 'title': 'P0', 'sequence': 1})]}),
            # closed
            self.env['survey.survey'].with_user(self.survey_manager).create({
                'title': 'S0',
                'active': False,
                'question_and_page_ids': [
                    (0, 0, {'is_page': True, 'question_type': False, 'title': 'P0', 'sequence': 1}),
                    (0, 0, {'title': 'Q0', 'sequence': 2, 'question_type': 'text_box'})
                ]
            })
        ]
        for survey in surveys:
            with self.assertRaises(UserError):
                survey.action_send_survey()

    @users('survey_manager')
    def test_survey_invite(self):
        Answer = self.env['survey.user_input']
        deadline = fields.Datetime.now() + relativedelta(months=1)

        self.survey.write({'access_mode': 'public', 'users_login_required': False})
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))

        # some lowlevel checks that action is correctly configured
        self.assertEqual(Answer.search([('survey_id', '=', self.survey.id)]), self.env['survey.user_input'])
        self.assertEqual(invite_form.survey_id, self.survey)

        invite_form.partner_ids.add(self.customer)
        invite_form.deadline = fields.Datetime.to_string(deadline)

        invite = invite_form.save()
        invite.action_invite()

        answers = Answer.search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(answers), 1)
        self.assertEqual(
            set(answers.mapped('email')),
            set([self.customer.email]))
        self.assertEqual(answers.mapped('partner_id'), self.customer)
        self.assertEqual(set(answers.mapped('deadline')), set([deadline]))

        with self.subTest('Warning when inviting an already invited partner'):
            action = self.survey.action_send_survey()
            invite_form = Form(self.env[action['res_model']].with_context(action['context']))
            invite_form.partner_ids.add(self.customer)

            self.assertIn(self.customer, invite_form.existing_partner_ids)
            self.assertEqual(invite_form.existing_text,
                             'The following customers have already received an invite: Caroline Customer.')


    @users('survey_manager')
    def test_survey_invite_authentication_nosignup(self):
        Answer = self.env['survey.user_input']

        self.survey.write({'access_mode': 'public', 'users_login_required': True})
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))

        with self.assertRaises(UserError):  # do not allow to add customer (partner without user)
            invite_form.partner_ids.add(self.customer)
        invite_form.partner_ids.clear()
        invite_form.partner_ids.add(self.user_portal.partner_id)
        invite_form.partner_ids.add(self.user_emp.partner_id)
        with self.assertRaises(UserError):
            invite_form.emails = 'test1@example.com, Raoulette Vignolette <test2@example.com>'
        invite_form.emails = False

        invite = invite_form.save()
        invite.action_invite()

        answers = Answer.search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(answers), 2)
        self.assertEqual(
            set(answers.mapped('email')),
            set([self.user_emp.email, self.user_portal.email]))
        self.assertEqual(answers.mapped('partner_id'), self.user_emp.partner_id | self.user_portal.partner_id)

    @users('survey_manager')
    def test_survey_invite_authentication_signup(self):
        self.env["ir.config_parameter"].sudo().set_param('auth_signup.invitation_scope', 'b2c')
        self.env.invalidate_all()
        Answer = self.env['survey.user_input']

        self.survey.write({'access_mode': 'public', 'users_login_required': True})
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))

        invite_form.partner_ids.add(self.customer)
        invite_form.partner_ids.add(self.user_portal.partner_id)
        invite_form.partner_ids.add(self.user_emp.partner_id)
        # TDE FIXME: not sure for emails in authentication + signup
        # invite_form.emails = 'test1@example.com, Raoulette Vignolette <test2@example.com>'

        invite = invite_form.save()
        invite.action_invite()

        answers = Answer.search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(answers), 3)
        self.assertEqual(
            set(answers.mapped('email')),
            set([self.customer.email, self.user_emp.email, self.user_portal.email]))
        self.assertEqual(answers.mapped('partner_id'), self.customer | self.user_emp.partner_id | self.user_portal.partner_id)

    @users('survey_manager')
    def test_survey_invite_email_from(self):
        # Verifies whether changing the value of the "email_from" field reflects on the receiving end.
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))
        invite_form.partner_ids.add(self.survey_user.partner_id)
        invite_form.template_id.write({'email_from':'{{ object.partner_id.email_formatted }}'})
        invite = invite_form.save()
        with self.mock_mail_gateway():
            invite.action_invite()

        self.assertEqual(len(self._new_mails), 1, "A new mail.mail should have been created")
        mail = self._new_mails[0]
        self.assertEqual(mail.email_from, self.survey_user.email_formatted)

    @users('survey_manager')
    def test_survey_invite_public(self):
        Answer = self.env['survey.user_input']

        self.survey.write({'access_mode': 'public', 'users_login_required': False})
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))

        invite_form.partner_ids.add(self.customer)
        invite_form.emails = 'test1@example.com, Raoulette Vignolette <test2@example.com>'

        invite = invite_form.save()
        invite.action_invite()

        answers = Answer.search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(answers), 3)
        self.assertEqual(
            set(answers.mapped('email')),
            set(['test1@example.com', '"Raoulette Vignolette" <test2@example.com>', self.customer.email]))
        self.assertEqual(answers.mapped('partner_id'), self.customer)

    @users('survey_manager')
    def test_survey_invite_token(self):
        Answer = self.env['survey.user_input']

        self.survey.write({'access_mode': 'token', 'users_login_required': False})
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))

        invite_form.partner_ids.add(self.customer)
        invite_form.emails = 'test1@example.com, Raoulette Vignolette <test2@example.com>'

        invite = invite_form.save()
        invite.action_invite()

        answers = Answer.search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(answers), 3)
        self.assertEqual(
            set(answers.mapped('email')),
            set(['test1@example.com', '"Raoulette Vignolette" <test2@example.com>', self.customer.email]))
        self.assertEqual(answers.mapped('partner_id'), self.customer)

    @users('survey_manager')
    def test_survey_invite_token_internal(self):
        Answer = self.env['survey.user_input']

        self.survey.write({'access_mode': 'token', 'users_login_required': True})
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))

        with self.assertRaises(UserError):  # do not allow to add customer (partner without user)
            invite_form.partner_ids.add(self.customer)
        with self.assertRaises(UserError):  # do not allow to add portal user
            invite_form.partner_ids.add(self.user_portal.partner_id)
        invite_form.partner_ids.clear()
        invite_form.partner_ids.add(self.user_emp.partner_id)
        with self.assertRaises(UserError):
            invite_form.emails = 'test1@example.com, Raoulette Vignolette <test2@example.com>'
        invite_form.emails = False

        invite = invite_form.save()
        invite.action_invite()

        answers = Answer.search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(answers), 1)
        self.assertEqual(
            set(answers.mapped('email')),
            set([self.user_emp.email]))
        self.assertEqual(answers.mapped('partner_id'), self.user_emp.partner_id)

    def test_survey_invite_token_by_email_nosignup(self):
        """
        Case: have multiples partners with the same email address
        If I set one email address, I expect one email to be sent
        """

        first_partner = self.env['res.partner'].create({
            'name': 'Test 1',
            'email': 'test@example.com',
        })

        self.env['res.partner'].create({
            'name': 'Test 2',
            'email': '"Raoul Poilvache" <TEST@example.COM>',
        })

        self.survey.write({'access_mode': 'token', 'users_login_required': False})
        action = self.survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))
        invite_form.emails = 'test@example.com'
        invite = invite_form.save()
        invite.action_invite()

        answers = self.env['survey.user_input'].search([('survey_id', '=', self.survey.id)])
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers.partner_id.display_name, first_partner.display_name)

    @users('survey_user')
    def test_survey_invite_with_template_attachment(self):
        """
        Test that a group_survey_user can send a survey that includes an attachment from the survey invite's
            email template
        """
        mail_template = self.env['mail.template'].create({
            'name': 'test mail template',
            'attachment_ids': [Command.create({
                'name': 'some_attachment.pdf',
                'res_model': 'mail.template',
                'datas': 'test',
                'type': 'binary',
            })],
        })

        user_survey = self.env['survey.survey'].create({
            'title': 'User Created Survey',
            'access_mode': 'public',
            'users_login_required': False,
            'users_can_go_back': False,
            'question_and_page_ids': [
                Command.create({
                    'title': 'First page',
                    'sequence': 1,
                    'is_page': True,
                    'question_type': False,
                }),
                Command.create({
                    'title': 'Test Free Text',
                    'sequence': 2,
                    'question_type': 'text_box',
                }),
            ]
        })

        action = user_survey.action_send_survey()
        invite_form = Form(self.env[action['res_model']].with_context(action['context']))
        invite_form.template_id = mail_template
        invite_form.emails = 'test_survey_invite_with_template_attachment@odoo.gov'
        invite = invite_form.save()
        with self.mock_mail_gateway():
            invite.action_invite()

        self.assertEqual(self.env['mail.mail'].sudo().search([
            ('email_to', '=', 'test_survey_invite_with_template_attachment@odoo.gov')
        ]).attachment_ids, mail_template.attachment_ids)
