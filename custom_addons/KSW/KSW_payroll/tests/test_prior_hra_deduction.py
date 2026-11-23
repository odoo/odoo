# -*- coding: utf-8 -*-
"""Tests for HRA double-payment prevention across overlapping payslips.

When a vacation payslip and a regular monthly payslip coexist for the
same employee/month, the HRA (House Rent Allowance) must only be paid
once.  The mechanism:

1. ``compute_sheet`` injects a ``PRIOR_HRA`` input line when it detects
   a prior confirmed payslip in the same period.
2. The HRA salary rule subtracts ``inputs.PRIOR_HRA`` from
   ``contract.hra``, effectively zeroing it out.
3. GOSI also uses the adjusted HRA amount.

Employee setup:
    wage=6000  hra=1500  da=0  travel=500  meal=300  medical=200  other=0
    Daily rate  = (6000 + 500 + 300 + 200) / 30 = 233.33
    GOSI base   = 6000 + 1500 = 7500 → 7500 × 9.75% = 731.25 → 731
"""
from datetime import date, datetime, time as dt_time

from odoo.tests.common import TransactionCase


class TestPriorHRADeduction(TransactionCase):
    """Ensure HRA is not paid twice when two payslips overlap the same month."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Calendar & schedule group ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Prior HRA Test Group',
        })
        for day in ['0', '1', '2', '3', '6']:
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Prior HRA Test Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Employee ──
        cls.employee = cls.env['hr.employee'].create({
            'name': 'HRA Test Employee',
            'resource_calendar_id': cls.calendar.id,
        })

        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'HRA Test Version',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': cls.calendar.id,
            'wage': 6000.0,
            'da': 0.0,
            'travel_allowance': 500.0,
            'meal_allowance': 300.0,
            'medical_allowance': 200.0,
            'other_allowance': 0.0,
            'hra': 1500.0,
            'struct_id': cls.env.ref('om_hr_payroll.structure_base').id,
        })
        cls.employee._compute_current_version_id()

        cls.month_start = date(2026, 4, 1)
        cls.month_end = date(2026, 4, 30)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_attendance(self, day, check_in_hour=8.0, check_out_hour=16.5):
        """Create a simple attendance record for the employee on a given day."""
        ci = datetime.combine(day, dt_time(int(check_in_hour), 0))
        co = datetime.combine(day, dt_time(int(check_out_hour), 30))
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': ci,
            'check_out': co,
        })

    def _create_payslip(self, name='Test Payslip', state='draft'):
        """Create a payslip for the test employee for the test month."""
        slip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'name': name,
            'date_from': self.month_start,
            'date_to': self.month_end,
            'struct_id': self.env.ref('om_hr_payroll.structure_base').id,
            'version_id': self.version.id,
        })
        return slip

    def _get_line_total(self, payslip, code):
        """Return the total of a specific salary line code."""
        line = payslip.line_ids.filtered(lambda l: l.code == code)
        return line[0].total if line else 0.0

    def _get_input_amount(self, payslip, code):
        """Return the amount of a specific input line code."""
        inp = payslip.input_line_ids.filtered(lambda i: i.code == code)
        return inp[0].amount if inp else 0.0

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_single_payslip_no_prior_hra(self):
        """A single payslip in a month should NOT have a PRIOR_HRA input."""
        # Create some attendance
        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        slip = self._create_payslip('Single Slip')
        slip.compute_sheet()

        prior_inputs = slip.input_line_ids.filtered(lambda i: i.code == 'PRIOR_HRA')
        self.assertFalse(prior_inputs, 'No PRIOR_HRA input should exist for a single payslip.')

        hra_total = self._get_line_total(slip, 'HRA')
        self.assertEqual(hra_total, 1500.0, 'HRA should be full 1500 for single payslip.')

    def test_prior_payslip_injects_prior_hra(self):
        """When a prior confirmed payslip exists, PRIOR_HRA input is injected."""
        # Create attendance for first 5 days
        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        # Create and confirm the "vacation payslip"
        vac_slip = self._create_payslip('Vacation Payslip')
        vac_slip.compute_sheet()

        # Verify vacation payslip has HRA
        vac_hra = self._get_line_total(vac_slip, 'HRA')
        self.assertEqual(vac_hra, 1500.0, 'Vacation payslip should have full HRA.')

        # Confirm the vacation payslip
        vac_slip.action_payslip_done()
        self.assertEqual(vac_slip.state, 'done')

        # Create the monthly payslip
        monthly_slip = self._create_payslip('Monthly Payslip')
        monthly_slip.compute_sheet()

        # Check PRIOR_HRA input was injected
        prior_hra_amount = self._get_input_amount(monthly_slip, 'PRIOR_HRA')
        self.assertEqual(prior_hra_amount, 1500.0,
                         'PRIOR_HRA input should equal the HRA already paid.')

        # Check HRA is 0 on the monthly payslip
        monthly_hra = self._get_line_total(monthly_slip, 'HRA')
        self.assertEqual(monthly_hra, 0.0,
                         'HRA should be 0 on the monthly payslip (already paid).')

    def test_prior_hra_with_verify_state(self):
        """PRIOR_HRA also works when prior payslip is in 'verify' state.

        Note: om_hr_payroll's compute_sheet() does NOT change the state;
        it stays 'draft'.  We manually set state='verify' to simulate
        the scenario where an HR user has computed but not yet confirmed.
        """
        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        vac_slip = self._create_payslip('Vacation Payslip')
        vac_slip.compute_sheet()

        # om_hr_payroll.compute_sheet keeps state='draft'; set 'verify'
        # manually to simulate HR reviewing the slip before confirmation.
        vac_slip.write({'state': 'verify'})
        self.assertEqual(vac_slip.state, 'verify')

        monthly_slip = self._create_payslip('Monthly Payslip')
        monthly_slip.compute_sheet()

        prior_hra = self._get_input_amount(monthly_slip, 'PRIOR_HRA')
        self.assertEqual(prior_hra, 1500.0,
                         'PRIOR_HRA should be injected even for verify-state prior payslips.')

        monthly_hra = self._get_line_total(monthly_slip, 'HRA')
        self.assertEqual(monthly_hra, 0.0)

    def test_cancelled_prior_payslip_ignored(self):
        """Cancelled payslips should NOT trigger PRIOR_HRA injection."""
        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        vac_slip = self._create_payslip('Cancelled Payslip')
        vac_slip.compute_sheet()
        # Cancel the payslip
        vac_slip.write({'state': 'cancel'})

        monthly_slip = self._create_payslip('Monthly Payslip')
        monthly_slip.compute_sheet()

        prior_inputs = monthly_slip.input_line_ids.filtered(lambda i: i.code == 'PRIOR_HRA')
        self.assertFalse(prior_inputs,
                         'Cancelled payslips should not trigger PRIOR_HRA injection.')

        monthly_hra = self._get_line_total(monthly_slip, 'HRA')
        self.assertEqual(monthly_hra, 1500.0, 'HRA should be full when prior is cancelled.')

    def test_draft_prior_payslip_ignored(self):
        """Draft payslips should NOT trigger PRIOR_HRA injection."""
        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        # Create but DON'T compute (stays in draft)
        vac_slip = self._create_payslip('Draft Payslip')
        self.assertEqual(vac_slip.state, 'draft')

        monthly_slip = self._create_payslip('Monthly Payslip')
        monthly_slip.compute_sheet()

        prior_inputs = monthly_slip.input_line_ids.filtered(lambda i: i.code == 'PRIOR_HRA')
        self.assertFalse(prior_inputs,
                         'Draft payslips should not trigger PRIOR_HRA injection.')

    def test_different_month_prior_payslip_ignored(self):
        """Payslips from a different month should NOT trigger PRIOR_HRA."""
        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        # Create a payslip for a different month (March)
        march_slip = self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'name': 'March Payslip',
            'date_from': date(2026, 3, 1),
            'date_to': date(2026, 3, 31),
            'struct_id': self.env.ref('om_hr_payroll.structure_base').id,
            'version_id': self.version.id,
        })
        march_slip.compute_sheet()
        march_slip.action_payslip_done()

        # Now create April payslip
        april_slip = self._create_payslip('April Payslip')
        april_slip.compute_sheet()

        prior_inputs = april_slip.input_line_ids.filtered(lambda i: i.code == 'PRIOR_HRA')
        self.assertFalse(prior_inputs,
                         'Different-month payslips should not trigger PRIOR_HRA.')

        april_hra = self._get_line_total(april_slip, 'HRA')
        self.assertEqual(april_hra, 1500.0, 'HRA should be full for April.')

    def test_recompute_clears_old_prior_hra(self):
        """Recomputing a payslip should refresh the PRIOR_HRA input."""
        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        vac_slip = self._create_payslip('Vacation Payslip')
        vac_slip.compute_sheet()
        vac_slip.action_payslip_done()

        monthly_slip = self._create_payslip('Monthly Payslip')
        monthly_slip.compute_sheet()

        # Verify PRIOR_HRA exists
        self.assertTrue(
            monthly_slip.input_line_ids.filtered(lambda i: i.code == 'PRIOR_HRA'))

        # Cancel the prior payslip
        vac_slip.write({'state': 'cancel'})

        # Recompute — should remove PRIOR_HRA
        monthly_slip.compute_sheet()

        prior_inputs = monthly_slip.input_line_ids.filtered(lambda i: i.code == 'PRIOR_HRA')
        self.assertFalse(prior_inputs,
                         'PRIOR_HRA should be removed after prior payslip is cancelled.')

        monthly_hra = self._get_line_total(monthly_slip, 'HRA')
        self.assertEqual(monthly_hra, 1500.0)

    def test_gosi_adjusted_when_hra_zeroed(self):
        """GOSI should be 0 on monthly payslip when already paid in full on vacation payslip."""
        # Make the employee Saudi for GOSI
        sa = self.env.ref('base.sa')
        self.employee.write({'country_id': sa.id})

        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        # Create and confirm vacation payslip
        vac_slip = self._create_payslip('Vacation Payslip')
        vac_slip.compute_sheet()
        vac_gosi = self._get_line_total(vac_slip, 'GOSI')
        # GOSI = -round((6000 + 1500) * 9.75 / 100) = -round(731.25) = -731
        self.assertEqual(vac_gosi, -731.0,
                         'Vacation payslip GOSI should be based on full basic+hra.')

        vac_slip.action_payslip_done()

        # Create monthly payslip
        monthly_slip = self._create_payslip('Monthly Payslip')
        monthly_slip.compute_sheet()

        monthly_gosi = self._get_line_total(monthly_slip, 'GOSI')
        # GOSI already paid in full (-731) on vacation payslip → monthly = 0
        self.assertEqual(monthly_gosi, 0.0,
                         'Monthly payslip GOSI should be 0 (already paid in full).')

    def test_gosi_full_when_no_prior(self):
        """GOSI should use full HRA when no prior payslip exists."""
        sa = self.env.ref('base.sa')
        self.employee.write({'country_id': sa.id})

        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        slip = self._create_payslip('Single Slip')
        slip.compute_sheet()

        gosi = self._get_line_total(slip, 'GOSI')
        self.assertEqual(gosi, -731.0,
                         'Single payslip GOSI should use full basic+hra.')

    def test_no_hra_employee_unaffected(self):
        """Employee with hra=0 should not have PRIOR_HRA injected."""
        self.version.write({'hra': 0.0})
        self.employee._compute_current_version_id()

        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        vac_slip = self._create_payslip('Vacation Payslip')
        vac_slip.compute_sheet()
        vac_slip.action_payslip_done()

        monthly_slip = self._create_payslip('Monthly Payslip')
        monthly_slip.compute_sheet()

        prior_inputs = monthly_slip.input_line_ids.filtered(lambda i: i.code == 'PRIOR_HRA')
        self.assertFalse(prior_inputs,
                         'No PRIOR_HRA when employee has no HRA.')

        # Restore for other tests
        self.version.write({'hra': 1500.0})

    def test_net_salary_reflects_hra_deduction(self):
        """The NET salary on the monthly payslip should be reduced by the
        HRA amount since it was already paid in the vacation payslip."""
        for d in range(1, 6):
            self._create_attendance(date(2026, 4, d))

        # Single payslip — establish baseline
        single_slip = self._create_payslip('Baseline Slip')
        single_slip.compute_sheet()
        single_net = self._get_line_total(single_slip, 'NET')
        single_hra = self._get_line_total(single_slip, 'HRA')

        self.assertEqual(single_hra, 1500.0)

        # Now confirm it and create a second payslip
        single_slip.action_payslip_done()

        second_slip = self._create_payslip('Second Slip')
        second_slip.compute_sheet()
        second_net = self._get_line_total(second_slip, 'NET')
        second_hra = self._get_line_total(second_slip, 'HRA')

        self.assertEqual(second_hra, 0.0, 'HRA should be zeroed on second slip.')

        # NET difference should be at least HRA amount (1500)
        # (Could be more due to GOSI adjustment)
        self.assertLess(second_net, single_net,
                        'Second payslip NET should be less than first due to HRA exclusion.')




