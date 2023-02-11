# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import socket

from odoo.addons.test_mail.tests.common import TestMailCommon, TestRecipients
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import formataddr


@tagged('multi_company')
class TestMultiCompanySetup(TestMailCommon, TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestMultiCompanySetup, cls).setUpClass()
        cls._activate_multi_company()

        cls.test_model = cls.env['ir.model']._get('mail.test.gateway')
        cls.email_from = '"Sylvie Lelitre" <test.sylvie.lelitre@agrolait.com>'

        cls.test_record = cls.env['mail.test.gateway'].with_context(cls._test_context).create({
            'name': 'Test',
            'email_from': 'ignasse@example.com',
        }).with_context({})

        cls.partner_1 = cls.env['res.partner'].with_context(cls._test_context).create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
        })
        # groups@.. will cause the creation of new mail.test.gateway
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'groups',
            'alias_user_id': False,
            'alias_model_id': cls.test_model.id,
            'alias_contact': 'everyone'})

        # Set a first message on public group to test update and hierarchy
        cls.fake_email = cls.env['mail.message'].create({
            'model': 'mail.test.gateway',
            'res_id': cls.test_record.id,
            'subject': 'Public Discussion',
            'message_type': 'email',
            'subtype_id': cls.env.ref('mail.mt_comment').id,
            'author_id': cls.partner_1.id,
            'message_id': '<123456-openerp-%s-mail.test.gateway@%s>' % (cls.test_record.id, socket.gethostname()),
        })

        cls._init_mail_gateway()

    @users('employee')
    def test_notify_reply_to_computation(self):
        test_record = self.env['mail.test.gateway'].browse(self.test_record.ids)
        res = test_record._notify_get_reply_to()
        self.assertEqual(
            res[test_record.id],
            formataddr((
                "%s %s" % (self.user_employee.company_id.name, test_record.name),
                "%s@%s" % (self.alias_catchall, self.alias_domain)))
        )

    @users('employee_c2')
    def test_notify_reply_to_computation_mc(self):
        """ Test reply-to computation in multi company mode. Add notably tests
        depending on user company_id / company_ids. """
        # Test1: no company_id field
        test_record = self.env['mail.test.gateway'].browse(self.test_record.ids)
        res = test_record._notify_get_reply_to()
        self.assertEqual(
            res[test_record.id],
            formataddr((
                "%s %s" % (self.user_employee_c2.company_id.name, test_record.name),
                "%s@%s" % (self.alias_catchall, self.alias_domain)))
        )

        # Test2: company_id field, MC environment
        self.user_employee_c2.write({'company_ids': [(4, self.user_employee.company_id.id)]})
        test_records = self.env['mail.test.multi.company'].create([
            {'name': 'Test',
             'company_id': self.user_employee.company_id.id},
            {'name': 'Test',
             'company_id': self.user_employee_c2.company_id.id},
        ])
        res = test_records._notify_get_reply_to()
        for test_record in test_records:
            self.assertEqual(
                res[test_record.id],
                formataddr((
                    "%s %s" % (self.user_employee_c2.company_id.name, test_record.name),
                    "%s@%s" % (self.alias_catchall, self.alias_domain)))
            )
