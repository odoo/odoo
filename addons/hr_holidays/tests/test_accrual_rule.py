from freezegun import freeze_time
from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form, HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon


@tagged('post_install', '-at_install')
class TestAccrualRule(BaseCommon):
    _test_user_groups = ('hr_holidays.group_hr_holidays_manager',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.time_type = cls.env['hr.work.entry.type'].create({
            'name': 'Accrued Time Off',
            'code': 'ACCRUAL_RULE_TEST',
            'requires_allocation': True,
            'time_off_selectable': True,
            'unit_of_measure': 'day',
            'country_id': False,
        })
        cls.other_company = cls.env['res.company'].create({'name': 'Other Accrual Company'})

    def _create_rule(self, **values):
        return self.env['hr.leave.accrual.rule'].create({
            'name': 'One Day per Month',
            'work_entry_type_id': self.time_type.id,
            **values,
        })

    @freeze_time('2026-02-28')
    def test_employee_seniority(self):
        employee = self.env['hr.employee'].sudo().create({'name': 'Seniority Employee'})
        self.assertFalse(employee.first_contract_date)
        self.assertFalse(employee.seniority)
        for contract_date, expected in [
            ('2026-02-28', '0 years, 0 months, 0 days'),
            ('2025-01-31', '1 years, 1 months, 0 days'),
            ('2024-02-29', '2 years, 0 months, 0 days'),
            ('2023-12-15', '2 years, 2 months, 13 days'),
            ('2026-03-01', False),
        ]:
            with self.subTest(contract_date=contract_date):
                employee.contract_date_start = contract_date
                self.assertEqual(employee.seniority, expected)

    def test_defaults_and_unit(self):
        rule = self._create_rule()
        self.assertTrue(rule.active)
        self.assertEqual(rule.company_id, self.env.company)
        self.assertEqual(rule.employee_domain, '[]')
        self.assertEqual(rule.frequency_count, 1)
        self.assertEqual(rule.frequency, 'month')
        self.assertEqual(rule.added_value, 1)
        self.assertEqual(rule.expiry_type, 'never')
        self.assertEqual(rule.unit_of_measure, 'day')
        self.time_type.unit_of_measure = 'hour'
        self.assertEqual(rule.unit_of_measure, 'hour')
        self.assertTrue(rule._fields['unit_of_measure'].readonly)

    @mute_logger('odoo.sql_db')
    def test_positive_values(self):
        for values in [
            {'frequency_count': 0},
            {'frequency_count': -1},
            {'added_value': 0},
            {'added_value': -1},
            {'expiry_type': 'delay', 'validity_count': 0},
            {'expiry_type': 'delay', 'validity_count': -1},
        ]:
            with self.subTest(values=values), self.assertRaises(IntegrityError), self.env.cr.savepoint():
                self._create_rule(**values)

    @mute_logger('odoo.sql_db')
    def test_fixed_expiry(self):
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._create_rule(expiry_type='fixed')
        rule = self._create_rule(expiry_type='fixed', date_to='2027-12-31')
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            rule.date_to = False
        self._create_rule(expiry_type='delay', validity_count=2, validity_type='month')

    @mute_logger('odoo.sql_db')
    def test_fixed_anchor(self):
        for frequency in ('week', 'month'):
            with self.subTest(frequency=frequency):
                with self.assertRaises(IntegrityError), self.env.cr.savepoint():
                    self._create_rule(frequency=frequency, anchor='fixed')
                self._create_rule(frequency=frequency, anchor='fixed', anchor_date='2026-01-01')
        self._create_rule(frequency='day', anchor='fixed')
        self._create_rule(frequency='year', anchor='fixed')

    def test_time_type_requires_allocation(self):
        self.time_type.requires_allocation = False
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._create_rule()

    def test_time_type_selectable(self):
        self.time_type.time_off_selectable = False
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._create_rule()

    def test_country_scope(self):
        country = self.env.ref('base.be')
        other_country = self.env.ref('base.us')
        self.time_type.country_id = country
        self._create_rule(company_id=False, country_id=country.id)
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._create_rule(company_id=False, country_id=other_country.id)

    def test_company_country_consistency(self):
        other_country = self.env.ref('base.be')
        if self.env.company.country_id == other_country:
            other_country = self.env.ref('base.us')
        if not self.env.company.country_id:
            self.env.company.sudo().country_id = self.env.ref('base.us')
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._create_rule(country_id=other_country.id)

    def test_company_access(self):
        own_rule = self._create_rule()
        shared_rule = self._create_rule(company_id=False)
        foreign_rule = self.env['hr.leave.accrual.rule'].sudo().create({
            'name': 'Other Company Rule',
            'work_entry_type_id': self.time_type.id,
            'company_id': self.other_company.id,
            'country_id': False,
        })
        rules = self.env['hr.leave.accrual.rule'].search([
            ('id', 'in', (own_rule | shared_rule | foreign_rule).ids),
        ])
        self.assertEqual(rules, own_rule | shared_rule)
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            foreign_rule.with_env(self.env).write({'name': 'Not Allowed'})

    def test_officer_read_only(self):
        rule = self._create_rule()
        self.env.user.sudo().group_ids = self.env.ref('hr_holidays.group_hr_holidays_user')
        self.assertEqual(rule.name, 'One Day per Month')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            rule.write({'added_value': 2})
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            self._create_rule()
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            rule.unlink()

    def test_employee_no_access(self):
        rule = self._create_rule()
        self.env.user.sudo().group_ids = self.env.ref('base.group_user')
        with self.assertRaises(AccessError), self.env.cr.savepoint():
            rule.read(['name'])

    def test_allocation_link_and_editable_start_date(self):
        rule = self._create_rule()
        employee = self.env['hr.employee'].create({'name': 'Accrual Employee'})
        allocation = self.env['hr.leave.allocation'].create({
            'employee_id': employee.id,
            'accrual_rule_id': rule.id,
            'date_from': '2026-01-01',
        })
        self.assertEqual(allocation.work_entry_type_id, rule.work_entry_type_id)
        self.assertEqual(allocation.state, 'validate')
        action = allocation.action_open_accrual_rule()
        self.assertEqual(action['res_model'], rule._name)
        self.assertEqual(action['res_id'], rule.id)
        with Form(allocation, view='hr_holidays.hr_leave_allocation_view_form_manager') as form:
            form.date_from = '2026-02-01'
        self.assertEqual(str(allocation.date_from), '2026-02-01')

    def test_allocation_company_consistency(self):
        rule = self._create_rule()
        employee = self.env['hr.employee'].sudo().create({
            'name': 'Other Company Employee',
            'company_id': self.other_company.id,
        })
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env['hr.leave.allocation'].sudo().create({
                'employee_id': employee.id,
                'accrual_rule_id': rule.id,
            })

    def test_rule_form(self):
        with Form(self.env['hr.leave.accrual.rule']) as form:
            form.name = 'UI Accrual Rule'
            form.work_entry_type_id = self.time_type
            form.frequency = 'day'
            with self.assertRaises(AssertionError):
                form.anchor = 'contract'
            form.frequency = 'week'
            form.anchor = 'fixed'
            with self.assertRaises(AssertionError):
                form.save()
            form.anchor_date = '2026-01-01'
            with self.assertRaises(AssertionError):
                form.validity_count = 2
            form.expiry_type = 'delay'
            form.validity_count = 2
            form.validity_type = 'month'
            with self.assertRaises(AssertionError):
                form.date_to = '2027-12-31'
            form.expiry_type = 'fixed'
            with self.assertRaises(AssertionError):
                form.save()
            form.date_to = '2027-12-31'
        self.assertEqual(form.record.expiry_type, 'fixed')

    def test_run_rule_creates_matching_allocations_once(self):
        matching, excluded = self.env['hr.employee'].create([
            {'name': 'Matching Accrual Employee'},
            {'name': 'Excluded Accrual Employee'},
        ])
        rule = self._create_rule(employee_domain=repr([('id', '=', matching.id)]))
        action = rule.action_run()
        allocations = self.env['hr.leave.allocation'].search(action['domain'])
        self.assertEqual(allocations.employee_id, matching)
        self.assertEqual(allocations.state, 'validate')
        self.assertEqual(allocations.work_entry_type_id, self.time_type)
        self.assertEqual(allocations.number_of_days, 0)
        allocations.number_of_days = 3
        rule.action_run()
        self.assertEqual(self.env['hr.leave.allocation'].search(action['domain']), allocations)
        self.assertEqual(allocations.number_of_days, 3)
        rule.employee_domain = repr([('id', '=', excluded.id)])
        rule.action_run()
        self.assertEqual(set(self.env['hr.leave.allocation'].search(action['domain']).employee_id.ids), set((matching | excluded).ids))

    def test_run_rule_no_match(self):
        rule = self._create_rule(employee_domain="[('id', '=', 0)]")
        action = rule.action_run()
        self.assertFalse(self.env['hr.leave.allocation'].search(action['domain']))

    def test_run_rule_relative_date_domain(self):
        recent, older = self.env['hr.employee'].create([
            {'name': 'Recent Employee', 'contract_date_start': fields.Date.today()},
            {'name': 'Older Employee', 'contract_date_start': fields.Date.subtract(fields.Date.today(), years=3)},
        ])
        rule = self._create_rule(employee_domain=repr([
            ('id', 'in', (recent | older).ids),
            ('first_contract_date', '>=', 'today -2y'),
        ]))
        action = rule.action_run()
        self.assertEqual(self.env['hr.leave.allocation'].search(action['domain']).employee_id, recent)

    def test_run_rule_country_scope(self):
        employee = self.env['hr.employee'].create({'name': 'Country Scoped Employee'})
        self.env.company.sudo().country_id = self.env.ref('base.be')
        rule = self._create_rule(
            company_id=False, country_id=self.env.ref('base.us').id,
            employee_domain=repr([('id', '=', employee.id)]),
        )
        action = rule.action_run()
        self.assertFalse(self.env['hr.leave.allocation'].search(action['domain']))

    def test_run_rule_scopes_employees(self):
        own_employee = self.env['hr.employee'].create({'name': 'Own Company Employee'})
        archived_employee = self.env['hr.employee'].create({'name': 'Archived Employee', 'active': False})
        other_employee = self.env['hr.employee'].sudo().create({
            'name': 'Other Company Employee',
            'company_id': self.other_company.id,
        })
        rule = self._create_rule(employee_domain=repr([
            ('id', 'in', (own_employee | archived_employee | other_employee).ids),
        ]))
        action = rule.action_run()
        self.assertEqual(self.env['hr.leave.allocation'].search(action['domain']).employee_id, own_employee)

    def test_run_rule_archived(self):
        rule = self._create_rule(active=False)
        with self.assertRaises(UserError):
            rule.action_run()

    def test_run_rule_invalid_domain(self):
        rule = self._create_rule(employee_domain='not a domain')
        with self.assertRaises(ValidationError):
            rule.action_run()

    def test_run_rule_officer_denied(self):
        rule = self._create_rule()
        self.env.user.sudo().group_ids = self.env.ref('hr_holidays.group_hr_holidays_user')
        with self.assertRaises(AccessError):
            rule.action_run()

    @mute_logger('odoo.sql_db')
    def test_rule_allocation_identity(self):
        employee = self.env['hr.employee'].create({'name': 'Accrual Employee'})
        rule = self._create_rule(employee_domain=repr([('id', '=', employee.id)]))
        rule.action_run()
        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self.env['hr.leave.allocation'].create({
                'employee_id': employee.id,
                'work_entry_type_id': self.time_type.id,
                'accrual_rule_id': rule.id,
            })


@tagged('post_install', '-at_install')
class TestAccrualRuleTour(HttpCase):

    def test_create_accrual_rule(self):
        self.env['hr.employee'].create([
            {
                'name': 'Recently Hired Accrual Employee',
                'contract_date_start': fields.Date.today(),
            },
            {
                'name': 'Long Serving Accrual Employee',
                'contract_date_start': fields.Date.subtract(fields.Date.today(), years=3),
            },
        ])
        time_type = self.env['hr.work.entry.type'].create({
            'name': 'Accrual Tour Time Off',
            'code': 'ACCRUAL_TOUR_TEST',
            'requires_allocation': True,
            'time_off_selectable': True,
            'unit_of_measure': 'day',
            'country_id': False,
        })
        self.start_tour('/odoo?debug=0', 'hr_holidays_accrual_rule_tour', login='admin')
        rule = self.env['hr.leave.accrual.rule'].search([('name', '=', 'UI Monthly Accrual')])
        self.assertEqual(len(rule), 1)
        self.assertEqual(rule.work_entry_type_id, time_type)
        self.assertEqual(rule.frequency, 'month')
        self.assertIn('first_contract_date', rule.employee_domain)
        allocations = self.env['hr.leave.allocation'].search([('accrual_rule_id', '=', rule.id)])
        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations.employee_id.name, 'Recently Hired Accrual Employee')
        self.assertEqual(allocations.state, 'validate')
        self.assertEqual(allocations.number_of_days, 0)
