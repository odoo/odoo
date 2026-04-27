# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from freezegun import freeze_time

from odoo import Command
from odoo.tests.common import TransactionCase


class TestPayrollCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
      super(TestPayrollCommon, cls).setUpClass()
      with freeze_time('2023-01-01'):
        today = date.today()
        cls.belgian_company = cls.env['res.company'].create({
            'name': 'My Belgian Company - Test',
            'country_id': cls.env.ref('base.be').id,
            'currency_id': cls.env.ref('base.EUR').id,
            'l10n_be_company_number': '0477472701',
            'l10n_be_revenue_code': '1293',
            'onss_expeditor_number': '123456',
            'street': 'Rue du Paradis',
            'zip': '6870',
            'city': 'Eghezee',
            'vat': 'BE0897223670',
            'phone': '061928374',
        })

        cls.env.user.company_ids |= cls.belgian_company
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=cls.belgian_company.ids))

        cls.holiday_leave_types = cls.env['hr.leave.type'].create([{
            'name': 'Paid Time Off',
            'requires_allocation': 'yes',
            'employee_requests': 'no',
            'allocation_validation_type': 'hr',
            'leave_validation_type': 'both',
            'responsible_ids': [Command.link(cls.env.ref('base.user_admin').id)],
            'request_unit': 'day'
        }])

        cls.resource_calendar = cls.env['resource.calendar'].create({
            'name': 'Test Calendar',
            'company_id': cls.belgian_company.id,
            'hours_per_day': 7.6,
            'tz': "Europe/Brussels",
            'two_weeks_calendar': False,
            'hours_per_week': 38,
            'full_time_required_hours': 38
        })

        cls.resource_calendar_mid_time = cls.resource_calendar.copy({
            'name': 'Calendar (Mid-Time)',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})
            ]
        })

        cls.resource_calendar_4_5 = cls.resource_calendar.copy({
            'name': 'Calendar (4 / 5)',
            'full_time_required_hours': 38,
            'attendance_ids': [
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
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'})
            ]
        })

        cls.resource_calendar_9_10 = cls.resource_calendar.copy({
            'name': 'Calendar (9 / 10)',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.6, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Friday Morning', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ]
        })

        cls.resource_calendar_30_hours_per_week = cls.resource_calendar.copy({
            'name': 'Calendar 30 Hours/Week',
            'full_time_required_hours': 38,
            'attendance_ids': [
                (0, 0, {'name': 'Monday Morning', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Monday Lunch', 'dayofweek': '0', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Monday Afternoon', 'dayofweek': '0', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Tuesday Morning', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tuesday Lunch', 'dayofweek': '1', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Tuesday Afternoon', 'dayofweek': '1', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Wednesday Morning', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wednesday Lunch', 'dayofweek': '2', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Wednesday Afternoon', 'dayofweek': '2', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'}),
                (0, 0, {'name': 'Thursday Morning', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thursday Lunch', 'dayofweek': '3', 'hour_from': 12, 'hour_to': 13, 'day_period': 'lunch'}),
                (0, 0, {'name': 'Thursday Afternoon', 'dayofweek': '3', 'hour_from': 13, 'hour_to': 16.5, 'day_period': 'afternoon'})
            ]
        })

        cls.employee_georges = cls.env['hr.employee'].create({
            'name': 'Georges',
            'private_country_id': cls.env.ref('base.be').id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.belgian_company.id,
            'marital': "single",
            'spouse_fiscal_status': "without_income",
            'disabled': False,
            'disabled_spouse_bool': False,
            'is_non_resident': False,
            'disabled_children_number': 0,
            'other_dependent_people': False,
            'other_senior_dependent': 0,
            'other_disabled_senior_dependent': 0,
            'other_juniors_dependent': 0,
            'other_disabled_juniors_dependent': 0,
            'fiscal_voluntary_rate': 0.0,
        })

        first_contract_georges = cls.env['hr.contract'].create({
            'name': "Georges's contract",
            'employee_id': cls.employee_georges.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.belgian_company.id,
            'structure_type_id': cls.env.ref('hr_contract.structure_type_employee_cp200').id,
            'date_start': date(today.year - 2, 1, 1),
            'date_end': date(today.year - 2, 12, 31),
            'wage': 2500.0,
            'hourly_wage': 0.0,
            'commission_on_target': 0.0,
            'fuel_card': 150.0,
            'internet': 38.0,
            'representation_fees': 150.0,
            'mobile': 30.0,
            'has_laptop': False,
            'meal_voucher_amount': 7.45,
            'eco_checks': 250.0,
            'ip': False,
            'ip_wage_rate': 25.0,
            'time_credit': False,
            'has_bicycle': False,
        })

        cls.georges_contracts = first_contract_georges

        cls.georges_contracts |= first_contract_georges.copy({
            'date_start': date(today.year - 1, 1, 1),
            'date_end': date(today.year - 1, 5, 31),
            'resource_calendar_id': cls.resource_calendar_mid_time.id,
            'wage': 1250
        })

        cls.georges_contracts |= first_contract_georges.copy({
            'date_start': date(today.year - 1, 6, 1),
            'date_end': date(today.year - 1, 8, 31),
        })

        cls.georges_contracts |= first_contract_georges.copy({
            'date_start': date(today.year - 1, 9, 1),
            'date_end': date(today.year - 1, 12, 31),
            'resource_calendar_id': cls.resource_calendar_4_5.id,
            'wage': 2500 * 4 / 5
        })

        cls.georges_contracts.write({'state': 'close'})  # By default, the state is 'draft' when we create a new contract

        contract = first_contract_georges.copy({
            'date_start': date(today.year, 1, 1),
            'date_end': False,
            'resource_calendar_id': cls.resource_calendar_4_5.id,
            'wage': 2500 * 4 / 5
        })
        contract.write({'state': 'open'})  # By default, the state is 'draft' when we create a new contract
        cls.georges_contracts |= contract

        cls.employee_john = cls.employee_georges.copy({
            'name': 'John Doe',
            'private_country_id': cls.env.ref('base.be').id,
            'resource_calendar_id': cls.resource_calendar.id,
            'contract_ids': []
        })

        first_contract_john = first_contract_georges.copy({
            'name': "John's Contract",
            'employee_id': cls.employee_john.id,
            'resource_calendar_id': cls.resource_calendar.id
        })

        cls.john_contracts = first_contract_john

        cls.john_contracts |= first_contract_john.copy({
            'date_start': date(today.year - 1, 1, 1),
            'date_end': date(today.year - 1, 3, 31)
        })

        cls.john_contracts |= first_contract_john.copy({
            'date_start': date(today.year - 1, 4, 1),
            'date_end': date(today.year - 1, 6, 30),
            'resource_calendar_id': cls.resource_calendar_9_10.id,
            'time_credit': True
        })

        cls.john_contracts |= first_contract_john.copy({
            'date_start': date(today.year - 1, 7, 1),
            'date_end': date(today.year - 1, 9, 30),
            'resource_calendar_id': cls.resource_calendar_4_5.id,
            'time_credit': True
        })

        cls.john_contracts.write({'state': 'close'})  # By default, the state is 'draft' when we create a new contract

        contract = first_contract_john.copy({
            'date_start': date(today.year - 1, 10, 1),
            'date_end': False,
            'resource_calendar_id': cls.resource_calendar_mid_time.id,
            'time_credit': True
        })
        contract.write({'state': 'open'})  # By default, the state is 'draft' when we create a new contract

        cls.john_contracts |= contract

        cls.employee_a = cls.employee_georges.copy({
            'name': 'A',
            'private_country_id': cls.env.ref('base.be').id,
            'resource_calendar_id': cls.resource_calendar.id,
            'contract_ids': []
        })

        first_contract_a = first_contract_georges.copy({
            'name': "A's Contract",
            'employee_id': cls.employee_a.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'date_start': date(today.year - 1, 1, 1),
            'date_end': False
        })

        first_contract_a.write({'state': 'open'})

        cls.a_contracts = first_contract_a

        cls.employee_test = cls.employee_georges.copy({
            'name': 'Employee Test',
            'private_country_id': cls.env.ref('base.be').id,
            'resource_calendar_id': cls.resource_calendar.id,
            'contract_ids': []
        })

        first_contract_test = first_contract_georges.copy({
            'name': "Employee Test's Contract",
            'employee_id': cls.employee_test.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'date_start': date(2017, 1, 1),
            'date_end': False
        })

        first_contract_test.write({'state': 'open'})

        cls.test_contracts = first_contract_test

        cls.double_pay_line = cls.env['l10n.be.double.pay.recovery.line'].create({
            'year': today.year - 1,
            'months_count': 3,
            'occupation_rate': 50,
            'amount': 1000
        })

        cls.employee_with_attestation = cls.employee_georges.copy({
            'name': 'Employee With Attestation',
            'first_contract_date': today,
            'private_country_id': cls.env.ref('base.be').id,
            'resource_calendar_id': cls.resource_calendar.id,
            'double_pay_line_ids': cls.double_pay_line,
            'contract_ids': []
        })

        first_contract_employee_with_attestation = first_contract_georges.copy({
            'name': "Employee with attestation Contract",
            'employee_id': cls.employee_with_attestation.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'date_start': date(today.year - 1, 10, 1),
            'date_end': date(today.year - 1, 12, 31),
        })

        cls.employee_with_attestation_contracts = first_contract_employee_with_attestation

        cls.employee_with_attestation_contracts.write({'state': 'close'})  # By default, the state is 'draft' when we create a new contract

        cls.employee_withholding_taxes = cls.env['hr.employee'].create({
            'name': 'EmployeeWithholdingTaxes',
            'resource_calendar_id': cls.resource_calendar.id,
            'company_id': cls.belgian_company.id,
        })

        cls.employee_withholding_taxes_contracts = first_contract_georges.copy({
            'name': "EmployeeWithholdingTaxes' Contract",
            'employee_id': cls.employee_withholding_taxes.id,
            'resource_calendar_id': cls.resource_calendar.id,
            'date_end': False,
            'internet': False,
            'mobile': False,
            'meal_voucher_amount': 0,
            'eco_checks': 0,
            'wage': 2500,
        })
        if 'wage_on_signature' in cls.env['hr.contract']:
            cls.employee_withholding_taxes_contracts['wage_on_signature'] = 2500

        cls.employee_withholding_taxes_contracts.write({'state': 'open'})  # By default, the state is 'draft' when we create a new contract
        cls.employee_withholding_taxes_contracts.generate_work_entries(cls.employee_withholding_taxes_contracts.date_start, today)
        cls.employee_withholding_taxes_payslip = cls.env['hr.payslip'].create({

            'name': "EmployeeWithholdingTaxes' Payslip",
            'employee_id': cls.employee_withholding_taxes.id,
            'contract_id': cls.employee_withholding_taxes_contracts.id,
        })
