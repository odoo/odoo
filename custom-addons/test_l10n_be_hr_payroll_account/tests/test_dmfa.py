# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from odoo.tests import common, tagged
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged('dmfa')
class TestDMFA(common.TransactionCase):

    def test_dmfa(self):
        user = mail_new_test_user(self.env, login='blou', groups='hr_payroll.group_hr_payroll_manager,fleet.fleet_group_manager')

        self.calendar_38h = self.env['resource.calendar'].create({
            'name': 'Standard 38 hours/week',
            'tz': 'Europe/Brussels',
            'company_id': False,
            'hours_per_day': 7.6,
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Friday Lunch', 'dayofweek': '4', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Friday Afternoon', 'dayofweek': '4', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ],
        })

        belgian_company = self.env['res.company'].create({
            'name': 'My Belgian Company - TEST',
            'country_id': self.env.ref('base.be').id,
        })

        lap = self.env['hr.employee'].create({
            'name': 'Laurie Poiret',
            'marital': 'single',
            'private_street': '58 rue des Wallons',
            'private_city': 'Louvain-la-Neuve',
            'private_zip': '1348',
            'private_country_id': self.env.ref("base.be").id,
            'private_phone': '+0032476543210',
            'private_email': 'laurie.poiret@example.com',
            'resource_calendar_id': self.calendar_38h.id,
            'company_id': belgian_company.id,
        })
        company = lap.company_id
        user.company_ids = [(4, company.id)]
        lap.address_id = lap.company_id.partner_id
        company.dmfa_employer_class = 456
        company.onss_registration_number = 45645
        company.onss_company_id = 45645
        self.env['l10n_be.dmfa.location.unit'].with_user(user).create({
            'company_id': lap.company_id.id,
            'code': 123,
            'partner_id': lap.address_id.id,
        })
        dmfa = self.env['l10n_be.dmfa'].with_user(user).create({
            'reference': 'TESTDMFA',
            'company_id': belgian_company.id
        })
        dmfa.with_context(dmfa_skip_signature=True).generate_dmfa_xml_report()
        self.assertFalse(dmfa.error_message)
        self.assertEqual(dmfa.validation_state, 'done')
