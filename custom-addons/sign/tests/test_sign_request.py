# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import Form, new_test_user
from .sign_request_common import SignRequestCommon
from odoo import Command
from odoo.exceptions import UserError, ValidationError

from datetime import datetime, timedelta

class TestSignRequest(SignRequestCommon):
    def test_sign_request_create(self):
        sign_request_no_item = self.create_sign_request_no_item(signer=self.partner_1, cc_partners=self.partner_4)

        sign_request_3_roles = self.create_sign_request_3_roles(customer=self.partner_1, employee=self.partner_2, company=self.partner_5, cc_partners=self.partner_4)

        for sign_request in [sign_request_no_item, sign_request_3_roles]:
            self.assertTrue(sign_request.exists(), 'A sign request with no sign item should be created')
            self.assertEqual(sign_request.state, 'sent', 'The default state for a new created sign request should be "sent"')
            self.assertTrue(all(sign_request.request_item_ids.mapped('is_mail_sent')), 'The mail should be sent for the new created sign request by default')
            self.assertEqual(sign_request.with_context(active_test=False).cc_partner_ids, self.partner_4, 'The cc_partners should be the specified one and the creator unless the creator is inactive')
            self.assertEqual(len(sign_request.sign_log_ids.filtered(lambda log: log.action == 'create')), 1, 'A log with action="create" should be created')
            for sign_request_item in sign_request:
                self.assertEqual(sign_request_item.state, 'sent', 'The default state for a new created sign request item should be "sent"')
        self.assertEqual(len(sign_request_no_item.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 1, 'An activity should be scheduled for signers with Sign Access')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 1, 'An activity should be scheduled for signers with Sign Access')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_2.id)), 1, 'An activity should be scheduled for signers with Sign Access')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_5.id)), 0, 'An activity should not be scheduled for signers without Sign Access')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_4.id)), 0, 'An activity should not be scheduled for CC partners')

        SignRequest = self.env['sign.request']
        with self.assertRaises(ValidationError, msg='A sign request with no sign item needs a signer'):
            SignRequest.create({
                'template_id': self.template_no_item.id,
                'reference': self.template_no_item.display_name,
            })

        with self.assertRaises(ValidationError, msg='A sign request with no sign item can only have the default role'):
            SignRequest.create({
                'template_id': self.template_no_item.id,
                'request_item_ids': [Command.create({
                    'partner_id': self.partner_1.id,
                    'role_id': self.env.ref('sign.sign_item_role_company').id,
                })],
                'reference': self.template_no_item.display_name,
            })

        with self.assertRaises(ValidationError, msg='Three roles need three singers'):
            SignRequest.create({
                'template_id': self.template_3_roles.id,
                'request_item_ids': [Command.create({
                    'partner_id': self.partner_1.id,
                    'role_id': self.env.ref('sign.sign_item_role_customer').id,
                }), Command.create({
                    'partner_id': self.partner_2.id,
                    'role_id': self.env.ref('sign.sign_item_role_employee').id,
                })],
                'reference': self.template_3_roles.display_name,
            })

        with self.assertRaises(ValidationError, msg='A role cannot be shared with two signers'):
            SignRequest.create({
                'template_id': self.template_3_roles.id,
                'request_item_ids': [Command.create({
                    'partner_id': self.partner_1.id,
                    'role_id': self.env.ref('sign.sign_item_role_customer').id,
                }), Command.create({
                    'partner_id': self.partner_2.id,
                    'role_id': self.env.ref('sign.sign_item_role_employee').id,
                }), Command.create({
                    'partner_id': self.partner_3.id,
                    'role_id': self.env.ref('sign.sign_item_role_company').id,
                }), Command.create({
                    'partner_id': self.partner_4.id,
                    'role_id': self.env.ref('sign.sign_item_role_company').id,
                })],
                'reference': self.template_3_roles.display_name,
            })

    def test_sign_request_no_item_create_sign_cancel_copy(self):
        # create
        sign_request_no_item = self.create_sign_request_no_item(signer=self.partner_1, cc_partners=self.partner_4)
        sign_request_item = sign_request_no_item.request_item_ids[0]

        # sign
        with self.assertRaises(UserError, msg='A sign.request.item can only sign its sign.items'):
            sign_request_item._edit_and_sign(self.customer_sign_values)
        sign_request_item._edit_and_sign(self.signature_fake)
        self.assertEqual(sign_request_item.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_no_item.state, 'signed', 'The sign request should be signed')
        self.assertEqual(len(sign_request_no_item.completed_document_attachment_ids), 2, 'The completed document and the certificate should be created')
        self.assertEqual(len(sign_request_no_item.sign_log_ids.filtered(
            lambda log: log.action == 'sign' and log.sign_request_item_id == sign_request_item)),
            1, 'A log with action="sign" should be created')
        self.assertEqual(len(sign_request_no_item.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 0, 'The activity should be removed after signing')
        with self.assertRaises(UserError, msg='A document cannot be signed twice'):
            sign_request_item._edit_and_sign(self.signature_fake)

        # cancel
        sign_request_item_token = sign_request_item.access_token
        sign_request_no_item_token = sign_request_no_item.access_token
        sign_request_no_item.cancel()
        self.assertEqual(sign_request_item.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_no_item.state, 'canceled', 'The sign request should be canceled')
        self.assertNotEqual(sign_request_item.access_token, sign_request_item_token, 'The access token should be changed')
        self.assertNotEqual(sign_request_no_item.access_token, sign_request_no_item_token, 'The access token should be changed')
        self.assertEqual(len(sign_request_no_item.sign_log_ids.filtered(lambda log: log.action == 'cancel')), 1, 'A log with action="cancel" should be created')

        # copy
        new_sign_request_no_item = sign_request_no_item.copy()
        self.assertTrue(new_sign_request_no_item.exists(), 'A sign request with no sign item should be created')
        self.assertEqual(new_sign_request_no_item.state, 'sent', 'The default state for a new created sign request should be "sent"')
        self.assertTrue(all(new_sign_request_no_item.request_item_ids.mapped('is_mail_sent')), 'The mail should be sent for the new created sign request by default')
        self.assertEqual(new_sign_request_no_item.with_context(active_test=False).cc_partner_ids, self.partner_4, 'The cc_partners should be the specified one and the creator unless he is inactive')
        self.assertEqual(len(new_sign_request_no_item.sign_log_ids.filtered(lambda log: log.action == 'create')), 1, 'A log with action="create" should be created')
        for sign_request_item in new_sign_request_no_item:
            self.assertEqual(sign_request_item.state, 'sent', 'The default state for a new created sign request item should be "sent"')
        self.assertNotEqual(new_sign_request_no_item.access_token, sign_request_no_item.access_token, 'The access_token should be changed')
        self.assertNotEqual(new_sign_request_no_item.request_item_ids[0].access_token, sign_request_no_item.request_item_ids[0].access_token, 'The access_token should be changed')

    def test_sign_request_3_roles_create_sign_cancel(self):
        # create
        sign_request_3_roles = self.create_sign_request_3_roles(customer=self.partner_1, employee=self.partner_2, company=self.partner_3, cc_partners=self.partner_4)
        role2sign_request_item = dict([(sign_request_item.role_id, sign_request_item) for sign_request_item in sign_request_3_roles.request_item_ids])
        sign_request_item_customer = role2sign_request_item[self.role_customer]
        sign_request_item_employee = role2sign_request_item[self.role_employee]
        sign_request_item_company = role2sign_request_item[self.role_company]

        # sign
        with self.assertRaises(UserError, msg='A sign.request.item can only sign its sign.items'):
            sign_request_item_employee._edit_and_sign(self.customer_sign_values)
        sign_request_item_customer._edit_and_sign(self.customer_sign_values)
        self.assertEqual(sign_request_item_customer.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_employee.state, 'sent', 'The sign.request.item should be sent')
        self.assertEqual(sign_request_item_company.state, 'sent', 'The sign.request.item should be sent')
        self.assertEqual(sign_request_3_roles.state, 'sent', 'The sign request should be signed')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(
            lambda log: log.action == 'sign' and log.sign_request_item_id == sign_request_item_customer)),
            1, 'A log with action="sign" should be created')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 0, 'The activity should be removed after signing')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_2.id)), 1, 'The activity should not be removed for unsigned signer')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_3.id)), 1, 'The activity should not be removed for unsigned signer')
        with self.assertRaises(UserError, msg='A document cannot be signed twice'):
            sign_request_item_customer._edit_and_sign(self.customer_sign_values)

        # cancel
        sign_request_item_customer_token = sign_request_item_customer.access_token
        sign_request_item_employee_token = sign_request_item_employee.access_token
        sign_request_item_company_token = sign_request_item_company.access_token
        sign_request_3_roles_token = sign_request_3_roles.access_token
        sign_request_3_roles.cancel()
        self.assertEqual(sign_request_item_customer.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_employee.state, 'canceled', 'The sign.request.item should be canceled')
        self.assertEqual(sign_request_item_company.state, 'canceled', 'The sign.request.item should be canceled')
        self.assertEqual(sign_request_3_roles.state, 'canceled', 'The sign request should be canceled')
        self.assertNotEqual(sign_request_item_customer.access_token, sign_request_item_customer_token, 'The access token should be changed')
        self.assertNotEqual(sign_request_item_employee.access_token, sign_request_item_employee_token, 'The access token should be changed')
        self.assertNotEqual(sign_request_item_company.access_token, sign_request_item_company_token, 'The access token should be changed')
        self.assertNotEqual(sign_request_3_roles.access_token, sign_request_3_roles_token, 'The access token should be changed')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(lambda log: log.action == 'cancel')), 1, 'A log with action="cancel" should be created')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_2.id)), 0, 'The activity should be removed after cancellation')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_3.id)), 0, 'The activity should be removed after cancellation')

    def test_sign_request_3_roles_create_sign_refuse_cancel(self):
        # create
        sign_request_3_roles = self.create_sign_request_3_roles(customer=self.partner_1, employee=self.partner_2, company=self.partner_3, cc_partners=self.partner_4)
        role2sign_request_item = dict([(sign_request_item.role_id, sign_request_item) for sign_request_item in sign_request_3_roles.request_item_ids])
        sign_request_item_customer = role2sign_request_item[self.role_customer]
        sign_request_item_employee = role2sign_request_item[self.role_employee]
        sign_request_item_company = role2sign_request_item[self.role_company]

        # sign (test has been done in test_sign_request_3_roles_create_sign_cancel)
        sign_request_item_customer._edit_and_sign(self.customer_sign_values)

        # refuse
        with self.assertRaises(UserError, msg='A signed sign.request.item cannot be refused'):
            sign_request_item_customer._refuse("bad document")
        sign_request_item_customer_token = sign_request_item_customer.access_token
        sign_request_item_employee_token = sign_request_item_employee.access_token
        sign_request_item_company_token = sign_request_item_company.access_token
        sign_request_3_roles_token = sign_request_3_roles.access_token
        sign_request_item_employee._refuse('bad document')
        self.assertEqual(sign_request_item_customer.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_employee.state, 'refused', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_company.state, 'canceled', 'The sign.request.item should be canceled')
        self.assertEqual(sign_request_3_roles.state, 'refused', 'The sign request should be refused')
        self.assertEqual(sign_request_item_customer.access_token, sign_request_item_customer_token, 'The access token should not be changed')
        self.assertEqual(sign_request_item_employee.access_token, sign_request_item_employee_token, 'The access token should not be changed')
        self.assertEqual(sign_request_item_company.access_token, sign_request_item_company_token, 'The access token should not be changed')
        self.assertEqual(sign_request_3_roles.access_token, sign_request_3_roles_token, 'The access token should not be changed')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(
            lambda log: log.action == 'refuse' and log.sign_request_item_id == sign_request_item_employee)),
            1, 'A log with action="refuse" should be created')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_2.id)), 0, 'The activity should be removed for refused signer')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_3.id)), 0, 'The activity should be removed for remaining signers')

        with self.assertRaises(UserError, msg='A canceled sign.request.item cannot be signed'):
            sign_request_item_company._edit_and_sign(self.company_sign_values)

        # cancel
        sign_request_3_roles.cancel()
        self.assertEqual(sign_request_item_customer.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_employee.state, 'refused', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_company.state, 'canceled', 'The sign.request.item should be canceled')
        self.assertEqual(sign_request_3_roles.state, 'canceled', 'The sign request should be canceled')
        self.assertNotEqual(sign_request_item_customer.access_token, sign_request_item_customer_token, 'The access token should be changed')
        self.assertNotEqual(sign_request_item_employee.access_token, sign_request_item_employee_token, 'The access token should be changed')
        self.assertNotEqual(sign_request_item_company.access_token, sign_request_item_company_token, 'The access token should be changed')
        self.assertNotEqual(sign_request_3_roles.access_token, sign_request_3_roles_token, 'The access token should be changed')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(lambda log: log.action == 'cancel')), 1, 'A log with action="cancel" should be created')

    def test_sign_request_item_auto_resend(self):
        # create
        sign_request = self.create_sign_request_no_item(signer=self.partner_1, cc_partners=self.partner_4)
        request_item_ids = sign_request.request_item_ids
        request_item = request_item_ids[0]
        token_a = request_item.access_token
        self.assertEqual(request_item.signer_email, "laurie.poiret.a@example.com", 'email address should be laurie.poiret.a@example.com')
        self.assertEqual(request_item.is_mail_sent, True, 'email should be sent')

        # resend the document
        request_item.send_signature_accesses()
        self.assertEqual(request_item.access_token, token_a, "sign request item's access token should not be changed")

        # change the email address of the signer (laurie.poiret.b)
        with self.assertRaises(ValidationError, msg='All signers must have valid email addresses'):
            self.partner_1.write({'email': 'laurie.poiret.b'})

        # change the email address of the signer (laurie.poiret.b@example.com)
        self.partner_1.write({'email': 'laurie.poiret.b@example.com'})
        token_b = request_item.access_token
        self.assertEqual(request_item.signer_email, "laurie.poiret.b@example.com", 'email address should be laurie.poiret.b@example.com')
        self.assertNotEqual(token_b, token_a, "sign request item's access token should be changed")
        self.assertEqual(len(sign_request.sign_log_ids.filtered(
            lambda log: log.action == 'update_mail' and log.sign_request_item_id == request_item)),
            1, 'A log with action="update_mail" should be created')
        self.assertEqual(len(sign_request.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 1, 'The number of activities should still be 1')

        # sign the document
        request_item._edit_and_sign(self.signature_fake)
        self.assertEqual(request_item.signer_email, "laurie.poiret.b@example.com", 'email address should be laurie.poiret.b@example.com')

        # change the email address of the signer (laurie.poiret.c@example.com)
        self.partner_1.write({'email': 'laurie.poiret.c@example.com'})
        token_c = request_item.access_token
        self.assertEqual(request_item.signer_email, "laurie.poiret.b@example.com", 'email address should be laurie.poiret.b@example.com')
        self.assertEqual(token_c, token_b, "sign request item's access token should be not changed after the document is signed by the signer")
        self.assertEqual(len(sign_request.sign_log_ids.filtered(
            lambda log: log.action == 'update_mail' and log.sign_request_item_id == request_item)),
            1, 'No new log with action="update_mail" should be created')

    def test_sign_request_item_reassign_sign_reassign_refuse_reassign(self):
        # create
        sign_request_3_roles = self.create_sign_request_3_roles(customer=self.partner_1, employee=self.partner_2,
                                                                company=self.partner_3, cc_partners=self.partner_4)
        role2sign_request_item = dict([(sign_request_item.role_id, sign_request_item) for sign_request_item in sign_request_3_roles.request_item_ids])
        sign_request_item_customer = role2sign_request_item[self.role_customer]
        sign_request_item_employee = role2sign_request_item[self.role_employee]
        sign_request_item_company = role2sign_request_item[self.role_company]

        # reassign
        self.assertEqual(sign_request_item_customer.signer_email, "laurie.poiret.a@example.com", 'email address should be laurie.poiret.a@example.com')
        self.assertEqual(sign_request_item_customer.is_mail_sent, True, 'email should be sent')
        token_customer = sign_request_item_customer.access_token
        with self.assertRaises(UserError, msg='Reassigning a role without change_authorized is not allowed'):
            sign_request_item_customer.write({'partner_id': self.partner_5.id})
        sign_request_item_customer.role_id.change_authorized = True
        with self.assertRaises(UserError, msg='Reassigning the partner_id to False is not allowed'):
            sign_request_item_customer.write({'partner_id': False})
        logs_num = len(sign_request_3_roles.sign_log_ids)
        sign_request_item_customer.write({'partner_id': self.partner_5.id})
        self.assertEqual(sign_request_item_customer.signer_email, "char.aznable.a@example.com", 'email address should be char.aznable.a@example.com')
        self.assertNotEqual(sign_request_item_customer.access_token, token_customer, "sign request item's access token should be changed")
        self.assertEqual(sign_request_item_customer.is_mail_sent, False, 'email should not be sent')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids), logs_num, 'No new log should be created')
        self.assertEqual(sign_request_3_roles.with_context(active_test=False).cc_partner_ids, self.partner_4 + self.partner_1, 'If a signer is reassigned and no longer be a signer, he should be a contact in copy')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 0, 'The activity for the old signer should be removed')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_5.id)), 0, 'No activity should be created for user without permission to access Sign')

        # sign
        sign_request_item_customer._edit_and_sign(self.customer_sign_values)

        # reassign
        token_employee = sign_request_item_customer.access_token
        with self.assertRaises(UserError, msg='A signed sign request item cannot be reassigned'):
            sign_request_item_customer.write({'partner_id': self.partner_1.id})
        sign_request_item_employee.role_id.change_authorized = True
        logs_num = len(sign_request_3_roles.sign_log_ids)
        sign_request_item_employee.write({'partner_id': self.partner_1.id})
        self.assertEqual(sign_request_item_employee.signer_email, "laurie.poiret.a@example.com", 'email address should be laurie.poiret.a@example.com')
        self.assertNotEqual(sign_request_item_employee.access_token, token_employee, "sign request item's access token should be changed")
        self.assertEqual(sign_request_item_employee.is_mail_sent, False, 'email should not be sent')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids), logs_num, 'No new log should be created')
        self.assertEqual(sign_request_3_roles.with_context(active_test=False).cc_partner_ids, self.partner_4 + self.partner_2, 'If a signer is reassigned and no longer be a signer, he should be a contact in copy')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_2.id)), 0, 'The activity for the old signer should be removed')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 1, 'An activity for the new signer should be created')

        # refuse
        sign_request_item_employee._refuse('bad request')

        # reassign
        with self.assertRaises(UserError, msg='A refused sign request item cannot be reassigned'):
            sign_request_item_employee.write({'partner_id': self.partner_2.id})
        with self.assertRaises(UserError, msg='A canceled sign request item cannot be reassigned'):
            sign_request_item_company.write({'partner_id': self.partner_2.id})

    def test_sign_request_no_item_create_editsign(self):
        # create
        sign_request_no_item = self.create_sign_request_no_item(signer=self.partner_1, cc_partners=self.partner_4)
        sign_request_item = sign_request_no_item.request_item_ids[0]
        template = sign_request_no_item.template_id
        sign_item_ids = template.sign_item_ids.ids

        # edit and sign
        value = 'edit and sign'
        new_sign_item_config = self.get_sign_item_config(sign_request_item.role_id.id)
        with self.assertRaises(UserError, msg='The key for new sign item should always < 0'):
            sign_request_item._edit_and_sign({'1': value}, new_sign_items={'1': new_sign_item_config})
        sign_request_item._edit_and_sign({'-1': value}, new_sign_items={'-1': new_sign_item_config})
        self.assertEqual(sign_request_item.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_no_item.state, 'signed', 'The sign request should be signed')
        self.assertEqual(len(sign_request_no_item.completed_document_attachment_ids), 2, 'The completed document and the certificate should be created')
        self.assertNotEqual(sign_request_no_item.template_id, template, 'An edited sign request should use a different template')
        self.assertEqual(template.sign_item_ids.ids, sign_item_ids, 'The original template should not be changed')
        self.assertEqual(len(sign_request_no_item.template_id.sign_item_ids.ids), len(sign_item_ids) + 1, 'The new template should have one more sign item')
        self.assertEqual(len(sign_request_no_item.sign_log_ids.filtered(lambda log: log.action == 'update')), 1, 'A log with action="update" should be created')
        self.assertEqual(len(sign_request_no_item.sign_log_ids.filtered(
            lambda log: log.action == 'sign' and log.sign_request_item_id == sign_request_item)),
            1, 'A log with action="sign" should be created')

    def test_sign_request_3_roles_editsign_sign_sign_unlink(self):
        # create
        sign_request_3_roles = self.create_sign_request_3_roles(customer=self.partner_1, employee=self.partner_2, company=self.partner_3, cc_partners=self.partner_4)
        role2sign_request_item = dict([(sign_request_item.role_id, sign_request_item) for sign_request_item in sign_request_3_roles.request_item_ids])
        sign_request_item_customer = role2sign_request_item[self.role_customer]
        sign_request_item_employee = role2sign_request_item[self.role_employee]
        sign_request_item_company = role2sign_request_item[self.role_company]
        template = sign_request_3_roles.template_id
        sign_item_ids = template.sign_item_ids.ids

        # edit and sign
        value = 'edit and sign'
        new_sign_item_config = self.get_sign_item_config(sign_request_item_customer.role_id.id)
        with self.assertRaises(UserError, msg='The key for new sign item should always < 0'):
            sign_request_item_customer._edit_and_sign(dict(self.customer_sign_values, **{'1': value}), new_sign_items={'1': new_sign_item_config})
        sign_request_item_customer._edit_and_sign(dict(self.customer_sign_values, **{'-1': value}), new_sign_items={'-1': new_sign_item_config})
        self.assertEqual(sign_request_item_customer.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_3_roles.state, 'sent', 'The sign request should be signed')
        self.assertNotEqual(sign_request_3_roles.template_id, template, 'An edited sign request should use a different template')
        self.assertEqual(template.sign_item_ids.ids, sign_item_ids, 'The original template should not be changed')
        self.assertEqual(len(sign_request_3_roles.template_id.sign_item_ids.ids), len(sign_item_ids) + 1, 'The new template should have one more sign item')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(lambda log: log.action == 'update')), 1, 'A log with action="update" should be created')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(
            lambda log: log.action == 'sign' and log.sign_request_item_id == sign_request_item_customer)),
            1, 'A log with action="sign" should be created')

        # sign
        with self.assertRaises(UserError, msg='Only the first signer can edit while signing'):
            sign_request_item_employee._edit_and_sign(
                dict(self.create_sign_values(sign_request_3_roles.template_id.sign_item_ids, sign_request_item_employee.role_id.id), **{'1': value}),
                new_sign_items={'-1': new_sign_item_config})
        sign_request_item_employee._edit_and_sign(
            self.create_sign_values(sign_request_3_roles.template_id.sign_item_ids, sign_request_item_employee.role_id.id))
        self.assertEqual(sign_request_item_customer.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_employee.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_company.state, 'sent', 'The sign.request.item should be sent')
        self.assertEqual(sign_request_3_roles.state, 'sent', 'The sign request should be sent')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(
            lambda log: log.action == 'sign' and log.sign_request_item_id == sign_request_item_employee)),
            1, 'A log with action="sign" should be created')

        # sign
        sign_request_item_company._edit_and_sign(
            self.create_sign_values(sign_request_3_roles.template_id.sign_item_ids, sign_request_item_company.role_id.id))
        self.assertEqual(sign_request_item_customer.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_employee.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_item_company.state, 'completed', 'The sign.request.item should be completed')
        self.assertEqual(sign_request_3_roles.state, 'signed', 'The sign request should be signed')
        self.assertEqual(len(sign_request_3_roles.completed_document_attachment_ids), 2, 'The completed document and the certificate should be created')
        self.assertEqual(len(sign_request_3_roles.sign_log_ids.filtered(
            lambda log: log.action == 'sign' and log.sign_request_item_id == sign_request_item_company)),
            1, 'A log with action="sign" should be created')

        # unlink
        sign_request_items = sign_request_3_roles.request_item_ids
        sign_item_values = sign_request_items.sign_item_value_ids
        sign_logs = sign_request_3_roles.sign_log_ids
        sign_request_3_roles.unlink()
        self.assertFalse(sign_request_items.exists(), 'All sign request items should be unlinked')
        self.assertFalse(sign_item_values.exists(), 'All sign item values should be unlinked')
        self.assertFalse(sign_logs.exists(), 'All sign logs should be unlinked')

    def test_sign_request_mail_sent_order(self):
        sign_request_3_roles = self.env['sign.request'].create({
            'template_id': self.template_3_roles.id,
            'reference': self.template_3_roles.display_name,
            'request_item_ids': [Command.create({
                'partner_id': self.partner_1.id,
                'role_id': self.env.ref('sign.sign_item_role_customer').id,
                'mail_sent_order': 1,
            }), Command.create({
                'partner_id': self.partner_2.id,
                'role_id': self.env.ref('sign.sign_item_role_employee').id,
                'mail_sent_order': 2,
            }), Command.create({
                'partner_id': self.partner_3.id,
                'role_id': self.env.ref('sign.sign_item_role_company').id,
                'mail_sent_order': 2,
            })],
        })
        role2sign_request_item = dict([(sign_request_item.role_id, sign_request_item) for sign_request_item in sign_request_3_roles.request_item_ids])
        sign_request_item_customer = role2sign_request_item[self.role_customer]
        sign_request_item_employee = role2sign_request_item[self.role_employee]
        sign_request_item_company = role2sign_request_item[self.role_company]
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_1.id)), 1, 'An activity should be scheduled for the first signer')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_2.id)), 0, 'No activity should be scheduled for the second signer')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_3.id)), 0, 'No activity should be scheduled for the third signer')
        self.assertTrue(sign_request_item_customer.is_mail_sent, 'An email should be sent for the first signer')
        self.assertFalse(sign_request_item_employee.is_mail_sent, 'No email should be sent for the second signer')
        self.assertFalse(sign_request_item_company.is_mail_sent, 'No email should be sent for the third signer')

        # sign
        sign_request_item_customer._edit_and_sign(self.customer_sign_values)
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_2.id)), 1, 'An activity should be scheduled for the second signer')
        self.assertEqual(len(sign_request_3_roles.activity_search(['mail.mail_activity_data_todo'], user_id=self.user_3.id)), 1, 'An activity should be scheduled for the third signer')
        self.assertTrue(sign_request_item_employee.is_mail_sent, 'An email should be sent for the second signer')
        self.assertTrue(sign_request_item_company.is_mail_sent, 'An email should be sent for the third signer')

        # sign and sign
        sign_request_item_employee._edit_and_sign(self.employee_sign_values)
        sign_request_item_company._edit_and_sign(self.company_sign_values)
        self.assertEqual(sign_request_3_roles.state, 'signed', 'The sign request should be signed')

    def test_sign_request_mail_reply_to_exists(self):
        sign_request = self.create_sign_request_1_role(self.partner_1, self.env['res.partner'])
        responsible_email = sign_request.create_uid.email_formatted
        mail = sign_request._message_send_mail(
            "body", 'mail.mail_notification_light',
            {'record_name': sign_request.reference},
            {'model_description': 'signature', 'company': self.env.company},
            {
                'email_from': responsible_email,
                'author_id': sign_request.create_uid.partner_id.id,
                'email_to': sign_request.request_item_ids[0].partner_id.name,
                'attachment_ids': [],
                'subject': sign_request.subject
            }
        )

        self.assertEqual(mail.reply_to, responsible_email, 'reply_to is not set as the responsible email')

    def test_sign_send_request_without_order(self):
        wizard = Form(self.env['sign.send.request'].with_context(active_id=self.template_3_roles.id, sign_directly_without_mail=False))
        self.assertEqual([record['mail_sent_order'] for record in wizard.signer_ids._records], [1, 1, 1])

    def test_sign_send_request_order_with_order(self):
        wizard = Form(self.env['sign.send.request'].with_context(active_id=self.template_3_roles.id, sign_directly_without_mail=False))
        wizard.set_sign_order = True
        self.assertEqual([record['mail_sent_order'] for record in wizard.signer_ids._records], [1, 2, 3])

    def test_archived_requests_dont_send_reminders(self):
        """ Create a request with old validity and archived, trigger cron reminder and ensure no reminder was created. """
        archived_request = self.create_sign_request_no_item(signer=self.partner_1, cc_partners=self.partner_4)
        archived_request.write({'active': False, 'validity': datetime.now() - timedelta(days=2)})
        self.env['sign.request']._cron_reminder()
        self.assertTrue(archived_request.state != 'expired')
