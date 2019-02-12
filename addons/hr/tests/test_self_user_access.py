# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.common import TestHrCommon
from odoo.tests import new_test_user
from odoo.exceptions import AccessError
from datetime import date
from collections import OrderedDict


class TestSelfAccessRights(TestHrCommon):

    def setUp(self):
        super(TestSelfAccessRights, self).setUp()
        self.richard = new_test_user(self.env, login='ric', groups='base.group_user', name='Simple employee', email='ric@example.com')
        self.richard_emp = self.env['hr.employee'].create({
            'name': 'Richard',
            'user_id': self.richard.id,
            'address_home_id': self.env['res.partner'].create({'name': 'Richard', 'phone': '21454', 'type': 'private'}).id,
        })
        self.hubert = new_test_user(self.env, login='hub', groups='base.group_user', name='Simple employee', email='hub@example.com')
        self.hubert_emp = self.env['hr.employee'].create({
            'name': 'Hubert',
            'user_id': self.hubert.id,
            'address_home_id': self.env['res.partner'].create({'name': 'Hubert', 'type': 'private'}).id,
        })

        self.protected_fields_emp = OrderedDict([(k, v) for k, v in self.env['hr.employee']._fields.items() if v.groups == 'hr.group_hr_user'])
        self.self_protected_fields_user = OrderedDict([
            (k, v)
            for k, v in self.env['res.users']._fields.items()
            if v.groups == 'hr.group_hr_user' and k in self.env['res.users'].SELF_READABLE_FIELDS
        ])

    # Read hr.employee #
    def testReadSelfEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.richard_emp.sudo(self.richard)[f]

    def testReadOtherEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.hubert_emp.sudo(self.richard)[f]

    # Write hr.employee #
    def testWriteSelfEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.richard_emp.sudo(self.richard).write({f: 'dummy'})

    def testWriteOtherEmployee(self):
        for f in self.protected_fields_emp:
            with self.assertRaises(AccessError):
                self.hubert_emp.sudo(self.richard).write({f: 'dummy'})

    # Read res.users #
    def testReadSelfUserEmployee(self):
        for f in self.self_protected_fields_user:
            self.richard.sudo(self.richard).read([f])  # should not raise

    def testReadOtherUserEmployee(self):

        for f in self.self_protected_fields_user:
            with self.assertRaises(AccessError, msg="Field %s should not be readable by other usrs" % f):
                self.hubert.sudo(self.richard)[f]

    # Write res.users #
    def testWriteSelfUserEmployeeSettingFalse(self):
        for f, v in self.self_protected_fields_user.items():
            with self.assertRaises(AccessError):
                self.richard.sudo(self.richard).write({f: 'dummy'})

    def testWriteSelfUserEmployee(self):
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', True)
        for f, v in self.self_protected_fields_user.items():
            val = None
            if v.type == 'char' or v.type == 'text':
                val = 'dummy'
            if val is not None:
                self.richard.sudo(self.richard).write({f: val})

    def testWriteSelfUserPreferencesEmployee(self):
        # self should always be able to update non hr.employee fields if
        # they are in SELF_READABLE_FIELDS
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', False)
        # should not raise
        vals = [
            {'tz': "Australia/ACT"},
            {'email': "new@example.com"},
            {'signature': "<p>I'm Richard!</p>"},
            {'notification_type': "email"},
        ]
        for v in vals:
            # should not raise
            self.richard.sudo(self.richard).write(v)

    def testWriteOtherUserPreferencesEmployee(self):
        # self should always be able to update non hr.employee fields if
        # they are in SELF_READABLE_FIELDS
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', False)
        vals = [
            {'tz': "Australia/ACT"},
            {'email': "new@example.com"},
            {'signature': "<p>I'm Richard!</p>"},
            {'notification_type': "email"},
        ]
        for v in vals:
            with self.assertRaises(AccessError):
                self.hubert.sudo(self.richard).write(v)

    def testWriteSelfPhoneEmployee(self):
        # phone is a related from res.partner (from base) but added in SELF_READABLE_FIELDS
        self.env['ir.config_parameter'].set_param('hr.hr_employee_self_edit', False)
        with self.assertRaises(AccessError):
            self.richard.sudo(self.richard).write({'phone': '2154545'})

    def testWriteOtherUserEmployee(self):

        for f in self.self_protected_fields_user:
            with self.assertRaises(AccessError):
                self.hubert.sudo(self.richard).write({f: 'dummy'})
