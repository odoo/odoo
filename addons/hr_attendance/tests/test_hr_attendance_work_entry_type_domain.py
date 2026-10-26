# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.tests import Form, TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestHrAttendanceWorkEntryTypeDomain(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        WorkEntryType = cls.env['hr.work.entry.type']
        cls.country_with_types = cls.env['res.country'].create({'name': 'Typeland', 'code': 'Q1'})
        cls.country_without_types = cls.env['res.country'].create({'name': 'Typeless', 'code': 'Q2'})

        def wet_vals(code, **vals):
            vals = {'name': code, 'code': code, **vals}
            if 'requires_allocation' in WorkEntryType._fields:
                vals.setdefault('requires_allocation', False)
            return vals

        cls.generic_type = WorkEntryType.create(wet_vals('TDOM_GEN', count_as='working_time', country_id=False))
        cls.country_type = WorkEntryType.create(
            wet_vals('TDOM_Q1', count_as='working_time', country_id=cls.country_with_types.id))
        cls.country_absence_type = WorkEntryType.create(
            wet_vals('TDOM_Q1_ABS', count_as='absence', country_id=cls.country_with_types.id))

        cls.company_with_types = cls.env['res.company'].create({
            'name': 'Company With Types', 'country_id': cls.country_with_types.id})
        cls.company_without_types = cls.env['res.company'].create({
            'name': 'Company Without Types', 'country_id': cls.country_without_types.id})
        cls.company_no_country = cls.env['res.company'].create({'name': 'Company Without Country'})
        cls.company_no_country.country_id = False

        cls.employees = cls.env['hr.employee'].create([{
            'name': company.name,
            'company_id': company.id,
            'tz': 'UTC',
        } for company in cls.company_with_types + cls.company_without_types + cls.company_no_country])

    def _create_attendances(self):
        return self.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2026, 1, 5, 8, 0),
            'check_out': datetime(2026, 1, 5, 12, 0),
            'work_entry_type_id': self.generic_type.id,
        } for employee in self.employees])

    def test_allowed_work_entry_types_by_country(self):
        att_with_types, att_without_types, att_no_country = self._create_attendances()
        generic_types = self.env['hr.work.entry.type'].search(
            att_without_types._get_work_entry_type_domain(country_ids=[]))
        self.assertIn(self.generic_type, generic_types)

        # country-specific working time types only (no generic one, no absence)
        self.assertEqual(att_with_types.allowed_work_entry_type_ids, self.country_type)
        # no type for the country: fall back on the generic working time types
        self.assertEqual(att_without_types.allowed_work_entry_type_ids, generic_types)
        self.assertEqual(att_no_country.allowed_work_entry_type_ids, generic_types)
        self.assertNotIn(self.country_absence_type, generic_types)

    def test_allowed_work_entry_types_single_record(self):
        """ The generic fallback must also work when computing a single record. """
        attendance = self._create_attendances()[1]
        attendance.invalidate_recordset(['allowed_work_entry_type_ids'])
        self.assertIn(self.generic_type, attendance.allowed_work_entry_type_ids)
        self.assertNotIn(self.country_type, attendance.allowed_work_entry_type_ids)

    def test_allowed_work_entry_types_onchange_employee(self):
        with Form(self.env['hr.attendance']) as attendance_form:
            attendance_form.employee_id = self.employees[0]
            self.assertEqual(attendance_form.allowed_work_entry_type_ids[:], self.country_type)
            attendance_form.employee_id = self.employees[1]
            self.assertIn(self.generic_type, attendance_form.allowed_work_entry_type_ids[:])
            attendance_form.work_entry_type_id = self.generic_type
            attendance_form.check_in = datetime(2026, 1, 5, 8, 0)
            attendance_form.check_out = datetime(2026, 1, 5, 12, 0)

    def test_allowed_work_entry_types_without_time_type_access(self):
        """ The domain is computed whenever the time type is displayed, also for users who
            cannot read the time types (e.g. no HR nor Time Off right). """
        user = new_test_user(self.env, login='tdom_user', groups='base.group_user',
                             company_id=self.company_with_types.id)
        group = self.env.ref('hr_holidays.group_hr_holidays_employee', raise_if_not_found=False)
        if group:
            user.group_ids -= group
        attendance = self._create_attendances()[0]
        attendance.employee_id.user_id = user
        attendance.invalidate_recordset(['allowed_work_entry_type_ids'])
        # no access error when the views read the domain field as the user
        attendance.with_user(user).web_read({'allowed_work_entry_type_ids': {}})
        self.assertEqual(attendance.allowed_work_entry_type_ids, self.country_type)
