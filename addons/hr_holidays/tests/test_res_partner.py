# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.tests.common import tagged, TransactionCase
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT

@tagged('post_install', '-at_install')
class TestPartner(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # use a single value for today throughout the tests to avoid weird scenarios around midnight
        cls.today = date.today()
        baseUser = cls.env['res.users'].create({
            'email': 'e.e@example.com',
            'groups_id': [Command.link(cls.env.ref('base.group_user').id)],
            'login': 'emp',
            'name': 'Ernest Employee',
            'notification_type': 'inbox',
            'signature': '--\nErnest',
        })
        cls.partner = baseUser.partner_id
        cls.users = baseUser + cls.env['res.users'].create({
            'name': 'test1',
            'login': 'test1',
            'email': 'test1@example.com',
            'partner_id': cls.partner.id,
        })
        cls.employees = cls.env['hr.employee'].create([{
            'user_id': user.id,
        } for user in cls.users])
        cls.leave_type = cls.env['hr.leave.type'].create({
            'leave_validation_type': 'no_validation',
            'requires_allocation': 'no',
            'name': 'Legal Leaves',
            'time_type': 'leave',
        })

    def test_res_partner_mail_partner_format(self):
        self.assertEqual(
            self.partner.mail_partner_format()[self.partner]['out_of_office_date_end'],
            False,
            'Partner is not considered out of office if one of their users is not on holiday',
        )

        self.env['hr.leave'].create([{
            'date_from': self.today + relativedelta(days=-2),
            'date_to': self.today + relativedelta(days=2),
            'employee_id': self.employees[0].id,
            'holiday_status_id': self.leave_type.id,
        }, {
            'date_from': self.today + relativedelta(days=-2),
            'date_to': self.today + relativedelta(days=3),
            'employee_id': self.employees[1].id,
            'holiday_status_id': self.leave_type.id,
        }])

        self.employees.invalidate_cache(fnames=['leave_date_to'])
        self.users.invalidate_cache(fnames=['leave_date_to'])
        self.assertEqual(
            self.partner.mail_partner_format()[self.partner]['out_of_office_date_end'],
            (self.today + relativedelta(days=2)).strftime(DEFAULT_SERVER_DATE_FORMAT),
            'Return date is the first return date of all users associated with a partner',
        )
