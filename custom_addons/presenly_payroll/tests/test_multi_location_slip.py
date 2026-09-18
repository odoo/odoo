from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase


class TestMultiLocationSlip(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.approver_user = new_test_user(
            cls.env,
            login='multi_loc_approver',
            groups='base.group_user,presenly.group_presenly_approver',
        )

        cls.address_jkt = cls.env['res.partner'].create({
            'name': 'JKT Office',
            'company_id': cls.company.id,
            'partner_latitude': -6.2,
            'partner_longitude': 106.8,
        })
        cls.address_bdg = cls.env['res.partner'].create({
            'name': 'BDG Office',
            'company_id': cls.company.id,
            'partner_latitude': -6.9,
            'partner_longitude': 107.6,
        })
        cls.location_jkt = cls.env['hr.work.location'].create({
            'name': 'Kantor Pusat Jakarta',
            'company_id': cls.company.id,
            'address_id': cls.address_jkt.id,
        })
        cls.location_bdg = cls.env['hr.work.location'].create({
            'name': 'Site Project Bandung',
            'company_id': cls.company.id,
            'address_id': cls.address_bdg.id,
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Multi-Location Employee',
            'company_id': cls.company.id,
            'work_location_id': cls.location_jkt.id,
        })
        cls.env['hr.version'].create({
            'employee_id': cls.employee.id,
            'date_version': '2030-01-01',
            'wage': 5000000.0,
        })

        cls.env['presenly.approval.rule'].sudo().search([
            ('is_overtime_route', '=', True),
            ('company_id', '=', cls.company.id),
        ]).write({'active': False})
        cls.env['presenly.approval.rule'].create({
            'name': 'Multi Loc Approver',
            'company_id': cls.company.id,
            'work_location_id': cls.location_jkt.id,
            'is_overtime_route': True,
            'sequence': 30,
            'approver_type': 'user',
            'approver_user_id': cls.approver_user.id,
        })
        cls.env['presenly.approval.rule'].create({
            'name': 'Multi Loc Approver BDG',
            'company_id': cls.company.id,
            'work_location_id': cls.location_bdg.id,
            'is_overtime_route': True,
            'sequence': 30,
            'approver_type': 'user',
            'approver_user_id': cls.approver_user.id,
        })

        cls.batch = cls.env['custom.payroll.batch'].create({
            'name': 'Payroll Aug 2030 Multi',
            'periode_bulan': '8',
            'periode_tahun': 2030,
            'company_id': cls.company.id,
        })

        cls.single_employee = cls.env['hr.employee'].create({
            'name': 'Single Location Employee',
            'company_id': cls.company.id,
            'work_location_id': cls.location_jkt.id,
        })
        cls.env['hr.version'].create({
            'employee_id': cls.single_employee.id,
            'date_version': '2030-01-01',
            'wage': 4000000.0,
        })

    def _add_attendance(self, employee, check_in_date, check_out_date,
                        location, worked_hours=8.0):
        att = self.env['hr.attendance']._presenly_mobile_create({
            'employee_id': employee.id,
            'check_in': f'{check_in_date} 08:00:00',
            'check_out': f'{check_out_date} 17:00:00',
            'presenly_work_location_id': location.id,
            'presenly_company_id': self.company.id,
            'presenly_source': 'mobile',
        })
        if worked_hours is not None:
            att.write({'worked_hours': worked_hours})
        return att

    def _create_approved_overtime(self, employee, location, hours=4.0,
                                  date_str='2030-08-01'):
        overtime = self.env['presenly.overtime.request'].create({
            'employee_id': employee.id,
            'work_location_id': location.id,
            'date': date_str,
            'hour_from': 18.0,
            'hour_to': 18.0 + hours,
            'reason': 'multi-loc test',
        })
        overtime.action_submit()
        overtime.with_user(self.approver_user).action_presenly_approve()
        self.assertEqual(overtime.state, 'approved')
        return overtime

    def _create_slip(self, employee, work_location=None, **kwargs):
        values = {
            'payroll_batch_id': self.batch.id,
            'employee_id': employee.id,
            'total_gaji_pokok': 5000000.0 if employee == self.employee else 4000000.0,
            'company_id': self.company.id,
        }
        if work_location:
            values['work_location_id'] = work_location.id
        values.update(kwargs)
        return self.env['custom.payroll.slip'].create(values)

    def test_wizard_creates_one_slip_per_location(self):
        """Generate wizard should emit 2 preview lines for multi-location employee."""
        self._add_attendance(self.employee, '2030-08-05', '2030-08-05',
                             self.location_jkt)
        self._add_attendance(self.employee, '2030-08-06', '2030-08-06',
                             self.location_bdg)
        wizard = self.env['custom.payroll.generate.wizard'].create({
            'payroll_batch_id': self.batch.id,
            'company_id': self.company.id,
            'employee_ids': [(6, 0, [self.employee.id, self.single_employee.id])],
            'skip_existing': True,
        })
        lines = wizard.preview_line_ids.filtered(
            lambda line: line.employee_id == self.employee
        )
        self.assertEqual(len(lines), 2,
                         'Multi-location employee must produce 2 preview lines.')
        location_ids = set(lines.mapped('work_location_id').ids)
        self.assertEqual(
            location_ids,
            {self.location_jkt.id, self.location_bdg.id},
        )
        for line in lines:
            self.assertEqual(line.work_location_count, 2)
            self.assertFalse(line.will_skip)

    def test_wizard_action_generate_creates_two_slips(self):
        self._add_attendance(self.employee, '2030-08-05', '2030-08-05',
                             self.location_jkt)
        self._add_attendance(self.employee, '2030-08-06', '2030-08-06',
                             self.location_bdg)
        wizard = self.env['custom.payroll.generate.wizard'].create({
            'payroll_batch_id': self.batch.id,
            'company_id': self.company.id,
            'employee_ids': [(6, 0, [self.employee.id])],
            'skip_existing': True,
        })
        wizard.action_generate()
        slips = self.batch.slip_ids.filtered(
            lambda s: s.employee_id == self.employee
        )
        self.assertEqual(len(slips), 2)
        for slip in slips:
            self.assertEqual(slip.total_gaji_pokok, 5000000.0,
                             'total_gaji_pokok must be FULL at every slip.')

    def test_unique_constraint_rejects_duplicate(self):
        self._create_slip(self.employee, self.location_jkt)
        with self.assertRaises(Exception):
            self._create_slip(self.employee, self.location_jkt)

    def test_overtime_is_filtered_by_location(self):
        self._add_attendance(self.employee, '2030-08-05', '2030-08-05',
                             self.location_jkt, worked_hours=10.0)
        self._add_attendance(self.employee, '2030-08-06', '2030-08-06',
                             self.location_bdg, worked_hours=10.0)
        self._create_approved_overtime(
            self.employee, self.location_jkt, hours=4.0, date_str='2030-08-05',
        )
        self._create_approved_overtime(
            self.employee, self.location_bdg, hours=3.0, date_str='2030-08-06',
        )
        slip_jkt = self._create_slip(self.employee, self.location_jkt)
        slip_bdg = self._create_slip(self.employee, self.location_bdg)
        self.assertAlmostEqual(slip_jkt.presenly_approved_hours, 4.0, places=4)
        self.assertAlmostEqual(slip_bdg.presenly_approved_hours, 3.0, places=4)

    def test_attendance_overtime_is_filtered_by_location(self):
        self._add_attendance(self.employee, '2030-08-05', '2030-08-05',
                             self.location_jkt, worked_hours=10.0)
        self._add_attendance(self.employee, '2030-08-06', '2030-08-06',
                             self.location_bdg, worked_hours=12.0)
        slip_jkt = self._create_slip(self.employee, self.location_jkt)
        slip_bdg = self._create_slip(self.employee, self.location_bdg)
        self.assertAlmostEqual(slip_jkt.attendance_overtime_hours, 2.0, places=4)
        self.assertAlmostEqual(slip_bdg.attendance_overtime_hours, 4.0, places=4)

    def test_slip_name_includes_location(self):
        slip = self._create_slip(self.employee, self.location_jkt)
        self.assertIn('Kantor-Pusat-Jakarta', slip.name)
        self.assertIn('/', slip.name)

    def test_split_by_location_creates_missing_slips(self):
        self._add_attendance(self.employee, '2030-08-05', '2030-08-05',
                             self.location_jkt)
        slip = self._create_slip(self.employee, self.location_jkt)
        with self.assertRaises(UserError):
            slip.action_split_by_location()

    def test_split_by_location_after_extra_attendance(self):
        self._add_attendance(self.employee, '2030-08-05', '2030-08-05',
                             self.location_jkt)
        self._add_attendance(self.employee, '2030-08-06', '2030-08-06',
                             self.location_bdg)
        slip_jkt = self._create_slip(self.employee, self.location_jkt)
        result = slip_jkt.action_split_by_location()
        self.assertTrue(result)
        all_employee_slips = self.batch.slip_ids.filtered(
            lambda s: s.employee_id == self.employee
        )
        self.assertEqual(len(all_employee_slips), 2)

    def test_single_location_backcompat_one_slip(self):
        self._add_attendance(self.single_employee, '2030-08-05', '2030-08-05',
                             self.location_jkt)
        wizard = self.env['custom.payroll.generate.wizard'].create({
            'payroll_batch_id': self.batch.id,
            'company_id': self.company.id,
            'employee_ids': [(6, 0, [self.single_employee.id])],
            'skip_existing': True,
        })
        wizard.action_generate()
        slips = self.batch.slip_ids.filtered(
            lambda s: s.employee_id == self.single_employee
        )
        self.assertEqual(len(slips), 1)
        self.assertEqual(slips.work_location_id, self.location_jkt)

    def test_attendance_summary_by_location(self):
        self._add_attendance(self.employee, '2030-08-05', '2030-08-05',
                             self.location_jkt, worked_hours=9.0)
        self._add_attendance(self.employee, '2030-08-06', '2030-08-06',
                             self.location_bdg, worked_hours=8.0)
        slip_jkt = self._create_slip(self.employee, self.location_jkt)
        summary = slip_jkt._get_attendance_summary_by_location()
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]['location_name'], 'Kantor Pusat Jakarta')
        self.assertEqual(summary[0]['days'], 1)
        self.assertAlmostEqual(summary[0]['worked_hours'], 9.0, places=2)
