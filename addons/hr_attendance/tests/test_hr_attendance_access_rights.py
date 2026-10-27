from datetime import datetime

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import common, tagged, new_test_user


@tagged('access_rights', 'post_install', '-at_install')
class TestHrAttendanceAccessRights(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = new_test_user(cls.env, login='attendance_rights_user', groups='base.group_user')
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Attendance Rights Employee',
            'user_id': cls.user.id,
        })

    def _set_groups(self, *xmlids):
        group_ids = [self.env.ref('base.group_user').id] + [self.env.ref(xmlid).id for xmlid in xmlids]
        self.user.group_ids = [Command.set(group_ids)]

    def test_create_own_attendance_access_progression(self):
        """Create access to one's own attendance, across group tiers."""
        # narrow officer only: no "own" grant and not their own manager
        self._set_groups('hr_attendance.group_hr_attendance_officer')
        with self.assertRaises(AccessError):
            self.env['hr.attendance'].with_user(self.user).create({
                'employee_id': self.employee.id,
                'check_in': datetime(2025, 1, 1, 8, 0, 0),
                'check_out': datetime(2025, 1, 1, 17, 0, 0),
            })

        # own only, under manual approval: creates fine, lands in draft, and the
        # work_entry_type_id-derived fields the web client reads right after
        # creation must be readable without HR department access
        self.env.company.attendance_validation = 'manual_validation'
        self._set_groups('hr_attendance.group_hr_attendance_own')
        attendance = self.env['hr.attendance'].with_user(self.user).create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')
        attendance_as_user = attendance.with_user(self.user)
        attendance_as_user.invalidate_recordset()
        self.assertTrue(attendance_as_user.wet_display_code or attendance_as_user.work_entry_type_id.name)

        # officer + own, under manual approval: holding officer rights over other
        # employees must not auto-validate this one's own record
        self._set_groups('hr_attendance.group_hr_attendance_officer', 'hr_attendance.group_hr_attendance_own')
        attendance = self.env['hr.attendance'].with_user(self.user).create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 1, 2, 8, 0, 0),
            'check_out': datetime(2025, 1, 2, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')

    def test_validate_own_attendance_access_progression(self):
        """Validate/refuse access to one's own attendance, across group tiers -
        including the direct write() bypass and self-assignment as own manager."""
        self.env.company.attendance_validation = 'manual_validation'

        # own only: write access to a draft own record exists (for check_in/out
        # edits), but writing 'state' to validated must still be
        # blocked
        self._set_groups('hr_attendance.group_hr_attendance_own')
        attendance = self.env['hr.attendance'].with_user(self.user).create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')
        with self.assertRaises(UserError):
            attendance.with_user(self.user).write({'state': 'validated'})
        self.assertEqual(attendance.state, 'draft')

        # officer + own: holding officer rights over other employees must not
        # let them validate/refuse their own record either
        self._set_groups('hr_attendance.group_hr_attendance_officer', 'hr_attendance.group_hr_attendance_own')
        attendance.state = 'draft'
        with self.assertRaises(UserError):
            attendance.with_user(self.user).action_validate()
        with self.assertRaises(UserError):
            attendance.with_user(self.user).action_refuse()
        self.assertEqual(attendance.state, 'draft')

        # "manage all": still not enough on its own to validate self - only being
        # your own attendance_manager (or Administrator) exempts you, and an
        # officer can't just assign themselves as their own manager
        self._set_groups('hr_attendance.group_hr_attendance_user')
        with self.assertRaises(UserError):
            attendance.with_user(self.user).action_validate()
        self.assertEqual(attendance.state, 'draft')
        with self.assertRaises(UserError):
            self.employee.with_user(self.user).attendance_manager_id = self.user
        # but if an Administrator deliberately sets it, they can validate
        self.employee.attendance_manager_id = self.user
        attendance.with_user(self.user).action_validate()
        self.assertEqual(attendance.state, 'validated')
        self.employee.attendance_manager_id = False

        # Administrator: exempt from the self-review restriction outright
        self._set_groups('hr_attendance.group_hr_attendance_manager')
        attendance.state = 'draft'
        attendance.with_user(self.user).action_validate()
        self.assertEqual(attendance.state, 'validated')

    def test_officer_cannot_assign_others_as_their_own_manager(self):
        """A 'manage all' officer can edit attendance_manager_id for other
        employees (that's the point of the field), but must not be able to make
        someone their own approver (only admin can create a
        self-referential attendance_manager_id.)"""
        self._set_groups('hr_attendance.group_hr_attendance_user')
        other_employee = self.env['hr.employee'].create({'name': 'Other Employee For Self Assign'})
        with self.assertRaises(UserError):
            other_employee.with_user(self.user).write({
                'user_id': self.user.id,
                'attendance_manager_id': self.user.id,
            })
        # an Administrator can still do it deliberately
        other_employee.write({'user_id': self.user.id, 'attendance_manager_id': self.user.id})
        self.assertEqual(other_employee.attendance_manager_id, self.user)

    def test_officer_manages_other_employees_attendance(self):
        """A narrow officer gets full access to an employee they
        manage: auto-validation on create, and the ability to validate a draft
        record belonging to that employee."""
        self._set_groups('hr_attendance.group_hr_attendance_officer')
        self.env.company.attendance_validation = 'manual_validation'
        managed_employee = self.env['hr.employee'].create({
            'name': 'Managed Employee',
            'attendance_manager_id': self.user.id,
        })

        attendance = self.env['hr.attendance'].with_user(self.user).create({
            'employee_id': managed_employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'validated', "officer managing this employee auto-validates on create")

        attendance.state = 'draft'
        attendance.with_user(self.user).action_validate()
        self.assertEqual(attendance.state, 'validated')

    def test_tolerance_auto_validation_still_works_for_self_edit_user(self):
        self._set_groups('hr_attendance.group_hr_attendance_own')
        self.env.company.write({
            'attendance_validation': 'tolerance_validation',
            'attendance_validation_tolerance': 100,
        })
        attendance = self.env['hr.attendance'].with_user(self.user).create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'validated')

    def test_self_edit_user_can_check_in_and_out_under_manual_validation(self):
        """simulate the systray check-in/check-out flow"""
        self._set_groups('hr_attendance.group_hr_attendance_own')
        self.env.company.attendance_validation = 'manual_validation'
        attendance = self.env['hr.attendance'].with_user(self.user).create({
            'employee_id': self.employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')
        attendance.with_user(self.user).write({
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.check_out, datetime(2025, 1, 1, 17, 0, 0))

    def test_work_entry_type_access_progression(self):
        """Time Type access across group tiers: officer/own only need read
        configuring it stays admin or alll officer only."""
        self._set_groups('hr_attendance.group_hr_attendance_officer')
        with self.assertRaises(AccessError):
            self.env['hr.work.entry.type'].with_user(self.user).create({
                'name': 'Should Not Be Allowed',
                'code': 'NOPE',
            })

        self._set_groups('hr_attendance.group_hr_attendance_user')
        work_entry_type = self.env['hr.work.entry.type'].with_user(self.user).create({
            'name': 'Test Time Type',
            'code': 'TESTWET',
        })
        work_entry_type.with_user(self.user).name = 'Test Time Type Renamed'
