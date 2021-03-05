# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase
from odoo.tests import tagged
from odoo.tests.common import new_test_user, users
from odoo.tools import formataddr


@tagged('res_identity')
class TestIdentity(TransactionCase):

    def setUp(self):
        super(TestIdentity, self).setUp()

        self.user_admin = self.env.ref('base.user_admin')
        self.user_admin.login = 'admin'

        # test standard employee
        self.user_employee = new_test_user(
            self.env, login='employee',
            groups='base.group_user',
            company_id=self.user_admin.company_id.id,
            name='Ernest Employee',
            signature='--\nErnest'
        )
        self.partner_employee = self.user_employee.partner_id

    @users('admin')
    def test_identity_name_create(self):
        """ Test name create, notably parsing given name to find an email """
        Identity = self.env['res.identity']
        name, email = "Micheline Beaujolais", "micheline@TEST.example.com"
        formatted = '"%s" <%s>' % (name, email)

        identity = Identity.browse(Identity.name_create(name)[0])
        self.assertEqual(identity.name, name)
        self.assertFalse(identity.email)

        identity = Identity.browse(Identity.name_create(formatted)[0])
        self.assertEqual(identity.name, name)
        self.assertEqual(identity.email, email.lower())
        self.assertEqual(identity.email_formatted, formataddr((name, email.lower())))
        self.assertEqual(identity.email_normalized, email.lower())
