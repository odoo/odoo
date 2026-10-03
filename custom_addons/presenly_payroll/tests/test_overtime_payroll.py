from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user
from odoo.tests.common import TransactionCase


class TestPresenlyPayrollOvertime(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.approver_user = new_test_user(
            cls.env,
            login='ot_payroll_approver',
            groups='base.group_user,presenly.group_presenly_approver',
        )
        cls.location_address = cls.env['res.partner'].create({
            'name': 'OT Payroll Address',
            'company_id': cls.company.id,
            'partner_latitude': -6.2,
            'partner_longitude': 106.8,
        })
        cls.location = cls.env['hr.work.location'].create({
            'name': 'OT Payroll Office',
            'company_id': cls.company.id,
            'address_id': cls.location_address.id,
            'presenly_manager_id': cls.approver_user.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'OT Payroll Employee',
            'company_id': cls.company.id,
            'work_location_id': cls.location.id,
        })
        cls.version = cls.env['hr.version'].create({
            'employee_id': cls.employee.id,
            'date_version': '2030-01-01',
            'wage': 3480000.0,
        })
        # 3480000 / 173 = 20115.6069...; hourly_rate is a Monetary field and is
        # rounded to 2 decimals by the currency, mirror that in expectations.
        cls.hourly_rate = round(3480000.0 / 173.0, 2)

        # Single-level overtime approval route. Deactivate any leftover overtime
        # routes in the shared dev DB so this test controls its own chain.
        cls.env['presenly.approval.rule'].sudo().search([
            ('is_overtime_route', '=', True),
            ('company_id', '=', cls.company.id),
        ]).write({'active': False})
        cls.env['presenly.approval.rule'].create({
            'name': 'OT Payroll Approver',
            'company_id': cls.company.id,
            'work_location_id': cls.location.id,
            'is_overtime_route': True,
            'sequence': 30,
            'approver_type': 'user',
            'approver_user_id': cls.approver_user.id,
        })

        cls.batch = cls.env['custom.payroll.batch'].create({
            'name': 'Payroll Aug 2030',
            'periode_bulan': '8',
            'periode_tahun': 2030,
            'company_id': cls.company.id,
        })

    def _add_attendance(self, date):
        """Attendance evidence for the given date (required before submit)."""
        return self.env['hr.attendance']._presenly_mobile_create({
            'employee_id': self.employee.id,
            'check_in': f'{date} 08:00:00',
            'check_out': f'{date} 17:00:00',
        })

    def _create_approved_overtime(self, date='2030-08-01', hour_from=18.0, hour_to=22.0):
        overtime = self.env['presenly.overtime.request'].create({
            'employee_id': self.employee.id,
            'work_location_id': self.location.id,
            'date': date,
            'hour_from': hour_from,
            'hour_to': hour_to,
            'reason': 'Server maintenance',
        })
        overtime.action_submit()
        overtime.with_user(self.approver_user).action_presenly_approve()
        self.assertEqual(overtime.state, 'approved')
        return overtime

    def _create_slip(self, **kwargs):
        values = {
            'payroll_batch_id': self.batch.id,
            'employee_id': self.employee.id,
            'total_gaji_pokok': 3480000.0,
            'company_id': self.company.id,
        }
        values.update(kwargs)
        return self.env['custom.payroll.slip'].create(values)

    def test_approved_requests_feed_payslip(self):
        self._add_attendance('2030-08-01')
        req = self._create_approved_overtime(hour_from=18.0, hour_to=22.0)
        self.assertAlmostEqual(req.duration_hours, 4.0, places=4)
        slip = self._create_slip()
        self.assertEqual(slip.presenly_approved_count, 1)
        self.assertAlmostEqual(slip.presenly_approved_hours, 4.0, places=4)
        self.assertAlmostEqual(slip.attendance_overtime_hours, 4.0, places=4)
        self.assertAlmostEqual(
            slip.overtime_amount, 4.0 * self.hourly_rate * 1.5, places=2,
        )
        detail = slip.detail_ids.filtered(
            lambda d: d.component_type == 'lembur'
        )
        self.assertEqual(len(detail), 1)
        self.assertIn('1 approved request', detail.description)
        self.assertAlmostEqual(detail.nominal, slip.overtime_amount, places=2)

    def test_attendance_extra_hours_are_ignored(self):
        # Attendance with 10+ worked hours WITHOUT any approved request must
        # not create overtime anymore (Presenly-only source).
        self._add_attendance('2030-08-05')
        slip = self._create_slip()
        self.assertEqual(slip.presenly_approved_count, 0)
        self.assertAlmostEqual(slip.presenly_approved_hours, 0.0, places=4)
        self.assertAlmostEqual(slip.attendance_overtime_hours, 0.0, places=4)
        self.assertEqual(
            slip.detail_ids.filtered(
                lambda d: d.component_type == 'lembur'
            ),
            self.env['custom.payroll.slip.detail'],
        )

    def test_only_approved_state_counts(self):
        # Each state on its own date (one request per day constraint).
        self._add_attendance('2030-08-01')
        self._add_attendance('2030-08-02')
        self._add_attendance('2030-08-03')
        self._add_attendance('2030-08-04')

        submitted = self.env['presenly.overtime.request'].create({
            'employee_id': self.employee.id,
            'work_location_id': self.location.id,
            'date': '2030-08-01',
            'hour_from': 18.0,
            'hour_to': 20.0,
        })
        submitted.action_submit()
        self.assertEqual(submitted.state, 'submitted')

        rejected = self.env['presenly.overtime.request'].create({
            'employee_id': self.employee.id,
            'work_location_id': self.location.id,
            'date': '2030-08-02',
            'hour_from': 18.0,
            'hour_to': 20.0,
        })
        rejected.action_submit()
        rejected.with_user(self.approver_user).action_presenly_reject('n/a')
        self.assertEqual(rejected.state, 'rejected')

        cancelled = self.env['presenly.overtime.request'].create({
            'employee_id': self.employee.id,
            'work_location_id': self.location.id,
            'date': '2030-08-03',
            'hour_from': 18.0,
            'hour_to': 20.0,
        })
        cancelled.action_submit()
        cancelled.action_cancel()
        self.assertEqual(cancelled.state, 'cancelled')

        draft = self.env['presenly.overtime.request'].create({
            'employee_id': self.employee.id,
            'work_location_id': self.location.id,
            'date': '2030-08-04',
            'hour_from': 18.0,
            'hour_to': 20.0,
        })
        self.assertEqual(draft.state, 'draft')

        slip = self._create_slip()
        self.assertEqual(slip.presenly_approved_count, 0)
        self.assertAlmostEqual(slip.presenly_approved_hours, 0.0, places=4)

    def test_period_boundary(self):
        # Requests outside the period (before/after) are excluded.
        self._add_attendance('2030-07-31')
        self._add_attendance('2030-09-01')
        self._create_approved_overtime(date='2030-07-31', hour_from=18.0, hour_to=22.0)
        self._create_approved_overtime(date='2030-09-01', hour_from=18.0, hour_to=22.0)
        slip = self._create_slip()
        self.assertEqual(slip.presenly_approved_count, 0)
        self.assertAlmostEqual(slip.presenly_approved_hours, 0.0, places=4)

    def test_manual_override_wins(self):
        self._add_attendance('2030-08-01')
        self._create_approved_overtime(hour_from=18.0, hour_to=22.0)
        slip = self._create_slip(overtime_override=5.0)
        self.assertAlmostEqual(slip.attendance_overtime_hours, 5.0, places=4)
        self.assertAlmostEqual(
            slip.overtime_amount, 5.0 * self.hourly_rate * 1.5, places=2,
        )

    def test_refresh_locked_on_paid_or_cancelled(self):
        self._add_attendance('2030-08-01')
        self._create_approved_overtime(hour_from=18.0, hour_to=22.0)
        slip = self._create_slip()
        slip.action_confirm()
        slip.action_paid()
        self.assertEqual(slip.status, 'paid')
        with self.assertRaises(UserError):
            slip.action_refresh_overtime()
        # Draft/confirmed can refresh.
        draft = self._create_slip()
        self.assertTrue(draft._presenly_overtime_domain())
        result = draft.action_refresh_overtime()
        self.assertTrue(result)

    def test_delete_log_on_approved_request(self):
        self._add_attendance('2030-08-01')
        req = self._create_approved_overtime(hour_from=18.0, hour_to=22.0)
        slip = self._create_slip()
        self.assertEqual(slip.presenly_approved_count, 1)
        # Admin deletes approved request with explicit confirmation.
        req.action_delete_with_confirm()
        self.assertFalse(req.exists())
        logs = self.env['presenly.deletion.log'].search([
            ('res_model', '=', 'presenly.overtime.request'),
            ('res_id', '=', req.id),
        ])
        self.assertEqual(len(logs), 1)
        draft_slip = self._create_slip()
        draft_slip.action_refresh_overtime()
        self.assertEqual(draft_slip.presenly_approved_count, 0)
        self.assertAlmostEqual(draft_slip.attendance_overtime_hours, 0.0, places=4)