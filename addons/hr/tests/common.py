# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests import common


class TestHrCommon(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.resource_calendar_id = cls.env['resource.calendar'].create({
            'attendance_ids': [
                (0, 0,
                    {
                        'dayofweek': weekday,
                        'hour_from': hour,
                        'hour_to': hour + 4,
                    })
                for weekday in ['0', '1', '2', '3', '4']
                for hour in [8, 13]
            ],
            'name': 'Standard 40h/week',
        })

        cls.res_users_hr_officer = mail_new_test_user(
            cls.env,
            email='hro@example.com',
            login='hro',
            groups='base.group_user,hr.group_hr_user,base.group_partner_manager',
            name='HR Officer',
        )

        cls.res_users_hr_manager = mail_new_test_user(
            cls.env,
            email='manager@example.com',
            login='manager',
            groups='base.group_user,hr.group_hr_manager,base.group_partner_manager',
            name='HR Admin',
        )

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Richard',
            'sex': 'male',
            'country_id': cls.env.ref('base.be').id,
        })
