from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError
from datetime import date, datetime
from odoo.tests import new_test_user


@tagged('hr_attendance_self_edit_role')
@tagged('at_install', '-post_install')
class TestHrAttendanceSelfEdit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
        })

        cls.admin = new_test_user(cls.env, login='user_admin', groups='hr_attendance.group_hr_attendance_manager', company_id=cls.company.id).with_company(cls.company)

        cls.user_self_edit = new_test_user(cls.env, login='user_self_edit', groups='hr_attendance.group_hr_attendance_own', company_id=cls.company.id).with_company(cls.company)
        cls.emp_self_edit = cls.env['hr.employee'].create({
            'name': "Youssef Ahmed",
            'user_id': cls.user_self_edit.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
        })

        cls.user_other = new_test_user(cls.env, login='user_other', groups='base.group_user', company_id=cls.company.id).with_company(cls.company)
        cls.emp_other = cls.env['hr.employee'].create({
            'name': "Ali Mohammed",
            'user_id': cls.user_other.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
        })

    def test_01_self_edit_own_attendance(self):
        """ Test a user with 'own' group can create and edit their own record """
        attendance = self.env['hr.attendance'].with_user(self.user_self_edit).create({
            'employee_id': self.emp_self_edit.id,
            'check_in': datetime(2023, 1, 1, 8, 0),
            'check_out': datetime(2023, 1, 1, 16, 0),
        })

        attendance._compute_can_edit()
        self.assertTrue(attendance.can_edit, "User should be able to edit their own pending attendance")

        attendance.write({'check_out': datetime(2023, 1, 1, 17, 0)})
        self.assertEqual(attendance.check_out, datetime(2023, 1, 1, 17, 0))

    def test_02_restrict_other_attendance(self):
        """ Test a user with 'own' group cannot edit someone else's attendance """
        attendance_other = self.env['hr.attendance'].create({
            'employee_id': self.emp_other.id,
            'check_in': datetime(2023, 1, 1, 8, 0),
            'check_out': datetime(2023, 1, 1, 16, 0),
        })

        with self.assertRaises(AccessError):
            attendance_other.with_user(self.user_self_edit).write({
                'check_out': datetime(2023, 1, 1, 18, 0)
            })


@tagged('post_install', '-at_install')
class TestHrAttendanceSelfEditViews(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'SweatChipChop Inc.'})
        cls.user_self_edit = new_test_user(
            cls.env, login='user_self_edit_views', groups='hr_attendance.group_hr_attendance_own',
            company_id=cls.company.id)
        cls.user_reader = new_test_user(
            cls.env, login='user_reader_views', groups='base.group_user', company_id=cls.company.id)
        cls.employees = cls.env['hr.employee'].create([{
            'name': user.name,
            'user_id': user.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
        } for user in cls.user_self_edit + cls.user_reader])
        cls.attendances = cls.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2023, 1, 2, 8, 0),
            'check_out': datetime(2023, 1, 2, 16, 0),
            'work_entry_type_id': cls.company.sudo().attendance_work_entry_type_id.id,
        } for employee in cls.employees])

    def test_my_attendances_without_hr_rights(self):
        """ Users without any HR / Time Off right must be able to open their attendances: the views
            display the time type, whose record is read with the user's rights. """
        for user in self.user_self_edit + self.user_reader:
            # holidays employees can already read the time types: make sure the user is not one of them
            group = self.env.ref('hr_holidays.group_hr_holidays_employee', raise_if_not_found=False)
            if group:
                user.group_ids -= group
            self.assertFalse(user.has_group('hr.group_hr_user'))
            Attendance = self.env['hr.attendance'].with_user(user).with_company(self.company)
            calendar_view = self.env.ref('hr_attendance.hr_attendance_my_calendar_view')
            form_view = self.env.ref('hr_attendance.hr_attendance_my_form_view')
            views = Attendance.get_views([(calendar_view.id, 'calendar'), (form_view.id, 'form'), (False, 'list')])
            for view_type in ('calendar', 'form', 'list'):
                fields = views['models']['hr.attendance']['fields']
                view_fields = views['views'][view_type].get('fields') or fields
                specification = {
                    fname: {'fields': {'display_name': {}}} if fields[fname]['type'] == 'many2one' else {}
                    for fname in view_fields if fname in fields
                }
                result = Attendance.web_search_read([('employee_id.user_id', '=', user.id)], specification)
                self.assertEqual(result['length'], 1)
                self.assertTrue(result['records'][0]['work_entry_type_id'])
            # time types displayed by the calendar filters and the many2one widgets
            work_entry_type = self.attendances.work_entry_type_id[:1]
            self.assertEqual(
                self.env['hr.work.entry.type'].with_user(user).search_read(
                    [('id', '=', work_entry_type.id)], ['color']),
                [{'id': work_entry_type.id, 'color': work_entry_type.color}])
            # overview cards of the attendance calendar: totals per time type
            employee = self.employees.filtered(lambda e: e.user_id == user)
            data = employee.with_user(user).get_attendance_data_by_employee(
                datetime(2023, 1, 1), datetime(2023, 1, 8))
            self.assertEqual(data[employee.id]['entries'][0]['worked_hours'], 8)
