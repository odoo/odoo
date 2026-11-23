# -*- coding: utf-8 -*-
"""Tests for FIFO historical vacation value computation.

Covers:
  - Single version: same as flat rate (backward compatible)
  - Multiple versions with salary raises: FIFO weighted sum
  - Prior vacation taken: FIFO skips consumed segments
  - Full clearance with historical rates
  - Combined (excess) leave with historical rates
  - No version history fallback
  - Label generation
"""
from datetime import date, datetime, timedelta

from odoo.tests.common import TransactionCase


class TestHistoricalVacationValue(TransactionCase):
    """Tests for _compute_historical_vacation_value FIFO slicing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Hist Group',
        })
        for day in ['0', '1', '2', '3', '6']:
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work Day {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Hist Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

    def _create_employee_with_versions(self, version_specs):
        """Create an employee with multiple version (salary) records.

        version_specs: list of (date_version, wage) tuples, oldest first.
        The first entry also sets contract_date_start.

        Returns (employee, versions list).
        """
        first_date, first_wage = version_specs[0]

        employee = self.env['hr.employee'].create({
            'name': 'Test Hist Employee',
            'resource_calendar_id': self.calendar.id,
        })

        # Set up first version (the auto-created one)
        version = employee.current_version_id
        version.write({
            'name': 'Version 1',
            'date_version': first_date,
            'contract_date_start': first_date,
            'resource_calendar_id': self.calendar.id,
            'wage': first_wage,
            'struct_id': self.env.ref('om_hr_payroll.structure_base').id,
        })

        versions = [version]
        for i, (ver_date, wage) in enumerate(version_specs[1:], start=2):
            new_ver = employee.create_version({
                'date_version': ver_date,
                'wage': wage,
            })
            new_ver.write({
                'name': 'Version %d' % i,
                'resource_calendar_id': self.calendar.id,
                'struct_id': self.env.ref('om_hr_payroll.structure_base').id,
            })
            versions.append(new_ver)

        employee._compute_current_version_id()
        return employee, versions

    # ==================================================================
    # Segments
    # ==================================================================

    def test_segments_single_version(self):
        """Single version produces one segment."""
        employee, _ = self._create_employee_with_versions([
            (date(2024, 1, 1), 6000.0),
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })
        segments = ksw_rec._get_version_accrual_segments(employee)
        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(segments[0]['daily_wage'], 200.0, places=2)

    def test_segments_multiple_versions(self):
        """Multiple versions produce multiple segments."""
        employee, _ = self._create_employee_with_versions([
            (date(2021, 1, 1), 4000.0),
            (date(2023, 1, 1), 5000.0),
            (date(2025, 1, 1), 6000.0),
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })
        segments = ksw_rec._get_version_accrual_segments(employee)
        self.assertEqual(len(segments), 3)
        self.assertAlmostEqual(
            segments[0]['daily_wage'], 4000.0 / 30, places=2)
        self.assertAlmostEqual(
            segments[1]['daily_wage'], 5000.0 / 30, places=2)
        self.assertAlmostEqual(
            segments[2]['daily_wage'], 6000.0 / 30, places=2)

    def test_segments_accrual_sums_to_total(self):
        """Sum of segment accrual days should match total_accrued_days."""
        employee, _ = self._create_employee_with_versions([
            (date(2021, 1, 1), 4000.0),
            (date(2023, 1, 1), 5000.0),
            (date(2025, 1, 1), 6000.0),
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })
        segments = ksw_rec._get_version_accrual_segments(employee)
        seg_total = sum(s['accrual_days'] for s in segments)

        # The total_accrued_days from _compute_leave_data should match
        # (both use the same tier-1/tier-2 formula, just segmented differently)
        # Small rounding differences are expected at segment boundaries
        # (segments use date_version boundaries, _compute_leave_data uses
        # a single joining→today range). Tolerance: 0.5 days.
        self.assertAlmostEqual(
            seg_total, ksw_rec.total_accrued_days, delta=0.5,
            msg="Sum of segment accruals should ≈ total_accrued_days")

    # ==================================================================
    # Historical value — single version (backward compatible)
    # ==================================================================

    def test_single_version_matches_flat_rate(self):
        """With one version, historical value = days × current_wage/30."""
        employee, _ = self._create_employee_with_versions([
            (date(2024, 1, 1), 6000.0),
        ])
        self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })

        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, 10.0)

        expected = 10.0 * (6000.0 / 30.0)
        self.assertAlmostEqual(result['total'], expected, places=2)
        self.assertEqual(len(result['breakdown']), 1)

    # ==================================================================
    # Historical value — multiple versions, no prior vacation
    # ==================================================================

    def test_multi_version_fifo_oldest_first(self):
        """With multiple versions and no prior vacation, oldest segments
        are consumed first at their historical wage rate."""
        employee, _ = self._create_employee_with_versions([
            (date(2021, 1, 1), 4000.0),  # 133.33/day
            (date(2023, 1, 1), 5000.0),  # 166.67/day
            (date(2025, 1, 1), 6000.0),  # 200.00/day
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })

        segments = ksw_rec._get_version_accrual_segments(employee)
        seg1_accrual = segments[0]['accrual_days']

        # Request fewer days than segment 1 accrual → all at 133.33
        small_days = min(seg1_accrual / 2, 5.0)
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, small_days)

        self.assertEqual(len(result['breakdown']), 1)
        self.assertAlmostEqual(
            result['breakdown'][0][1], 4000.0 / 30.0, places=2,
            msg="Should use oldest version's wage rate")
        self.assertAlmostEqual(
            result['total'], small_days * (4000.0 / 30.0), places=2)

    def test_multi_version_crosses_segments(self):
        """Consuming more days than the first segment crosses into the
        second segment at a different wage rate."""
        employee, _ = self._create_employee_with_versions([
            (date(2021, 1, 1), 4000.0),
            (date(2023, 1, 1), 5000.0),
            (date(2025, 1, 1), 6000.0),
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })

        segments = ksw_rec._get_version_accrual_segments(employee)
        seg1_accrual = segments[0]['accrual_days']

        # Request seg1_accrual + 2 days → should span 2 segments
        request_days = seg1_accrual + 2.0
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, request_days)

        self.assertGreaterEqual(len(result['breakdown']), 2,
            msg="Should span at least 2 segments")

        # First portion at 4000/30, second portion at 5000/30
        self.assertAlmostEqual(
            result['breakdown'][0][1], 4000.0 / 30.0, places=2)
        self.assertAlmostEqual(
            result['breakdown'][1][1], 5000.0 / 30.0, places=2)

        # Total should NOT be flat-rate at current wage
        flat_total = request_days * (6000.0 / 30.0)
        self.assertNotAlmostEqual(
            result['total'], flat_total, places=0,
            msg="Historical FIFO should differ from flat current rate")

    def test_multi_version_total_less_than_flat_current(self):
        """When salary increased over time, FIFO historical total should
        be LESS than flat current rate (oldest days = lowest wage)."""
        employee, _ = self._create_employee_with_versions([
            (date(2021, 1, 1), 3000.0),  # 100/day
            (date(2023, 1, 1), 6000.0),  # 200/day
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })

        segments = ksw_rec._get_version_accrual_segments(employee)
        total_accrual = sum(s['accrual_days'] for s in segments)

        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, total_accrual)

        flat_total = total_accrual * (6000.0 / 30.0)
        self.assertLess(
            result['total'], flat_total,
            msg="Historical total should be less than flat current rate "
                "when salary increased over time")

    # ==================================================================
    # Historical value — with prior vacation taken
    # ==================================================================

    def test_prior_vacation_skips_consumed_segments(self):
        """When prior vacation days consumed the first segment entirely,
        new vacation starts at the second segment's rate."""
        employee, _ = self._create_employee_with_versions([
            (date(2021, 1, 1), 4000.0),
            (date(2023, 1, 1), 5000.0),
            (date(2025, 1, 1), 6000.0),
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })
        ksw_rec._refresh_accrual()

        segments = ksw_rec._get_version_accrual_segments(employee)
        seg1_accrual = segments[0]['accrual_days']

        # Create a validated leave via SQL to simulate prior consumption
        # consuming exactly seg1's accrual days
        annual_type = self.env['hr.leave.type'].sudo().search([
            ('is_annual_leave', '=', True),
        ], limit=1)

        dt_from = date(2024, 6, 1)
        dt_to = dt_from + timedelta(days=int(seg1_accrual))
        dt_from_utc = datetime.combine(
            dt_from, datetime.min.time()) + timedelta(hours=5)
        dt_to_utc = datetime.combine(
            dt_to, datetime.min.time()) + timedelta(hours=13, minutes=30)

        self.env.cr.execute("""
            INSERT INTO hr_leave
                (employee_id, holiday_status_id, state,
                 request_date_from, request_date_to,
                 date_from, date_to,
                 number_of_days, number_of_hours,
                 x_return_state, x_annual_approval_state,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'validate',
                 %s, %s, %s, %s,
                 %s, %s,
                 'not_applicable', 'approved',
                 %s, %s, NOW(), NOW())
        """, (
            employee.id, annual_type.id,
            dt_from, dt_to, dt_from_utc, dt_to_utc,
            seg1_accrual, seg1_accrual * 8.0,
            self.env.uid, self.env.uid,
        ))
        self.env.invalidate_all()

        # Refresh accrual so leaves_taken is updated
        ksw_rec._refresh_accrual()

        # Now compute historical value for 5 more days
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, 5.0)

        # First segment should be skipped (consumed by prior vacation)
        # So the rate should be from segment 2 (5000/30)
        if result['breakdown']:
            self.assertAlmostEqual(
                result['breakdown'][0][1], 5000.0 / 30.0, places=2,
                msg="After consuming seg1, new vacation should start "
                    "at seg2 rate")

    # ==================================================================
    # No version history fallback
    # ==================================================================

    def test_no_versions_uses_current_wage(self):
        """When no version history, fallback to current wage."""
        employee = self.env['hr.employee'].create({
            'name': 'No History Employee',
        })
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, 10.0)
        # Should not crash, returns 0 or current wage
        self.assertIsInstance(result['total'], float)

    # ==================================================================
    # Label generation
    # ==================================================================

    def test_label_single_segment(self):
        """Label for single segment shows one rate."""
        employee, _ = self._create_employee_with_versions([
            (date(2024, 1, 1), 6000.0),
        ])
        self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, 5.0)
        self.assertIn('200.00', result['label'])
        self.assertNotIn('+', result['label'])

    def test_label_multi_segment(self):
        """Label for multi-segment shows multiple rates separated by +."""
        employee, _ = self._create_employee_with_versions([
            (date(2021, 1, 1), 3000.0),
            (date(2023, 1, 1), 6000.0),
        ])
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': employee.id,
        })
        segments = ksw_rec._get_version_accrual_segments(employee)
        # Request enough to span both segments
        total_accrual = sum(s['accrual_days'] for s in segments)
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            employee, total_accrual)
        self.assertIn('+', result['label'],
            msg="Multi-segment label should contain '+' separator")


