# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import fields, models
from odoo.models import add_to_registry
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSchedulingMixin(TransactionCase):
    """Test the resource scheduling mixin fields and methods.

    Uses a standard 40h/week calendar (Mon-Fri, 8:00-12:00 + 13:00-17:00 UTC)
    and various resource configurations to validate the consolidated scheduling
    logic.

    Reference dates (2025):
        Mon 2025-01-06  |  Tue 2025-01-07  |  Wed 2025-01-08
        Thu 2025-01-09  |  Fri 2025-01-10  |  Sat 2025-01-11
        Sun 2025-01-12  |  Mon 2025-01-13
    """

    MODEL_NAME = 'resource.scheduling.test'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # -- Register a concrete test model inheriting the mixin --
        class SchedulingTest(models.Model):
            _module = 'resource'
            _name = cls.MODEL_NAME
            _description = 'Scheduling Mixin Test Model'
            _inherit = ['resource.scheduling.mixin']

            name = fields.Char()
            company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

        add_to_registry(cls.registry, SchedulingTest)
        cls.registry._setup_models__(cls.env.cr, [])
        cls.registry.init_models(
            cls.env.cr, [cls.MODEL_NAME], {'module': 'resource'},
        )

        # Standard 40h/week calendar (Mon-Fri 8-12 + 13-17, UTC)
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test 40h Calendar',
            'tz': 'UTC',
        })

        # Regular resource using the standard calendar
        cls.resource = cls.env['resource.resource'].create({
            'name': 'Test Resource',
            'calendar_id': cls.calendar.id,
            'tz': 'UTC',
        })

        # Flexible resource (calendar with flexible_hours=True)
        cls.flex_calendar = cls.env['resource.calendar'].create({
            'name': 'Flexible 35h Calendar',
            'tz': 'UTC',
            'flexible_hours': True,
            'hours_per_day': 7.0,
            'full_time_required_hours': 35,
        })
        cls.flex_resource = cls.env['resource.resource'].create({
            'name': 'Flex Resource',
            'calendar_id': cls.flex_calendar.id,
            'tz': 'UTC',
        })

        # Fully flexible resource (no calendar at all)
        cls.fully_flex_resource = cls.env['resource.resource'].create({
            'name': 'Fully Flex Resource',
            'calendar_id': False,
            'tz': 'UTC',
        })

        cls.Model = cls.env[cls.MODEL_NAME]

    # ------------------------------------------------------------------
    # Allocated hours — calendar-aware computation
    # ------------------------------------------------------------------

    def test_allocated_hours_with_calendar(self):
        """Mon 8:00 → Mon 17:00 with standard calendar = 8h (excludes lunch)."""
        record = self.Model.create({
            'name': 'Single day',
            'date_start': datetime(2025, 1, 6, 8, 0),   # Mon 8:00
            'date_end': datetime(2025, 1, 6, 17, 0),     # Mon 17:00
            'resource_id': self.resource.id,
        })
        self.assertEqual(record.allocated_hours, 8.0)

    def test_allocated_hours_cross_day(self):
        """Mon 8:00 → Tue 17:00 = 16h (two full work days)."""
        record = self.Model.create({
            'name': 'Cross day',
            'date_start': datetime(2025, 1, 6, 8, 0),   # Mon 8:00
            'date_end': datetime(2025, 1, 7, 17, 0),     # Tue 17:00
            'resource_id': self.resource.id,
        })
        self.assertEqual(record.allocated_hours, 16.0)

    def test_allocated_hours_cross_weekend(self):
        """Fri 8:00 → Mon 17:00 = 16h (skips Sat + Sun)."""
        record = self.Model.create({
            'name': 'Cross weekend',
            'date_start': datetime(2025, 1, 10, 8, 0),  # Fri 8:00
            'date_end': datetime(2025, 1, 13, 17, 0),   # Mon 17:00
            'resource_id': self.resource.id,
        })
        self.assertEqual(record.allocated_hours, 16.0)

    def test_allocated_hours_no_resource(self):
        """No resource → uses company calendar (not raw timedelta)."""
        record = self.Model.create({
            'name': 'No resource',
            'date_start': datetime(2025, 1, 6, 8, 0),   # Mon 8:00
            'date_end': datetime(2025, 1, 6, 17, 0),    # Mon 17:00
        })
        # Should use company calendar (standard 40h/week) → 8h
        self.assertEqual(record.resource_id.id, False)
        self.assertGreater(record.allocated_hours, 0.0)
        self.assertEqual(record.allocated_hours, 8.0)

    def test_allocated_hours_flexible_resource(self):
        """Flexible resource: work hours capped by flex calendar constraints."""
        record = self.Model.create({
            'name': 'Flexible',
            'date_start': datetime(2025, 1, 6, 0, 0),   # Mon 00:00
            'date_end': datetime(2025, 1, 10, 23, 59),   # Fri 23:59
            'resource_id': self.flex_resource.id,
        })
        # 35h/week flex calendar across a full work week
        self.assertAlmostEqual(record.allocated_hours, 35.0, places=0)

    def test_allocated_percentage(self):
        """50% allocation of an 8h slot = 4h."""
        record = self.Model.create({
            'name': '50% allocation',
            'date_start': datetime(2025, 1, 6, 8, 0),   # Mon 8:00
            'date_end': datetime(2025, 1, 6, 17, 0),     # Mon 17:00
            'resource_id': self.resource.id,
            'allocated_percentage': 50.0,
        })
        self.assertEqual(record.allocated_hours, 4.0)

    # ------------------------------------------------------------------
    # Calendar snapping
    # ------------------------------------------------------------------

    def test_snap_to_calendar(self):
        """Midnight → should snap to first work interval (8:00)."""
        record = self.Model.create({
            'name': 'Snap test',
            'resource_id': self.resource.id,
        })
        snapped_start, snapped_end = record._scheduling_snap_to_calendar(
            datetime(2025, 1, 6, 0, 0),   # Mon midnight
            datetime(2025, 1, 6, 23, 59),  # Mon 23:59
            calendar=self.calendar,
        )
        self.assertEqual(snapped_start.hour, 8)
        self.assertEqual(snapped_end.hour, 17)

    # ------------------------------------------------------------------
    # Plan hours (inverse computation)
    # ------------------------------------------------------------------

    def test_plan_hours(self):
        """16 working hours from Mon 8:00 → should end Tue 17:00."""
        record = self.Model.create({
            'name': 'Plan hours',
            'resource_id': self.resource.id,
        })
        end = record._scheduling_plan_hours(
            16.0,
            datetime(2025, 1, 6, 8, 0),   # Mon 8:00
            resource=self.resource,
            calendar=self.calendar,
        )
        self.assertIsNotNone(end)
        # 8h Mon + 8h Tue = 16h → Tue 17:00
        self.assertEqual(end, datetime(2025, 1, 7, 17, 0))

    # ------------------------------------------------------------------
    # Overlap detection
    # ------------------------------------------------------------------

    def test_overlap_detection(self):
        """Two 100% slots on same resource at same time → conflict."""
        rec1 = self.Model.create({
            'name': 'Slot A',
            'date_start': datetime(2025, 1, 6, 8, 0),
            'date_end': datetime(2025, 1, 6, 17, 0),
            'resource_id': self.resource.id,
            'allocated_percentage': 100.0,
        })
        rec2 = self.Model.create({
            'name': 'Slot B',
            'date_start': datetime(2025, 1, 6, 8, 0),
            'date_end': datetime(2025, 1, 6, 17, 0),
            'resource_id': self.resource.id,
            'allocated_percentage': 100.0,
        })
        # Force recompute
        rec1.invalidate_recordset(['schedule_overlap_count'])
        rec2.invalidate_recordset(['schedule_overlap_count'])
        self.assertGreater(rec1.schedule_overlap_count, 0)
        self.assertGreater(rec2.schedule_overlap_count, 0)

    def test_overlap_percentage(self):
        """Two 50% slots → no conflict; two 60% slots → conflict."""
        rec1 = self.Model.create({
            'name': 'Slot 50A',
            'date_start': datetime(2025, 1, 6, 8, 0),
            'date_end': datetime(2025, 1, 6, 17, 0),
            'resource_id': self.resource.id,
            'allocated_percentage': 50.0,
        })
        rec2 = self.Model.create({
            'name': 'Slot 50B',
            'date_start': datetime(2025, 1, 6, 8, 0),
            'date_end': datetime(2025, 1, 6, 17, 0),
            'resource_id': self.resource.id,
            'allocated_percentage': 50.0,
        })
        rec1.invalidate_recordset(['schedule_overlap_count'])
        rec2.invalidate_recordset(['schedule_overlap_count'])
        # 50 + 50 = 100 → not > 100 → no conflict
        self.assertEqual(rec1.schedule_overlap_count, 0)
        self.assertEqual(rec2.schedule_overlap_count, 0)

        # Now bump to 60% each → 120% > 100 → conflict
        rec1.allocated_percentage = 60.0
        rec2.allocated_percentage = 60.0
        rec1.flush_recordset()
        rec2.flush_recordset()
        rec1.invalidate_recordset(['schedule_overlap_count'])
        rec2.invalidate_recordset(['schedule_overlap_count'])
        self.assertGreater(rec1.schedule_overlap_count, 0)
        self.assertGreater(rec2.schedule_overlap_count, 0)

    def test_no_overlap_different_resource(self):
        """Same time, different resources → no conflict."""
        resource2 = self.env['resource.resource'].create({
            'name': 'Other Resource',
            'calendar_id': self.calendar.id,
            'tz': 'UTC',
        })
        rec1 = self.Model.create({
            'name': 'Resource 1 slot',
            'date_start': datetime(2025, 1, 6, 8, 0),
            'date_end': datetime(2025, 1, 6, 17, 0),
            'resource_id': self.resource.id,
            'allocated_percentage': 100.0,
        })
        rec2 = self.Model.create({
            'name': 'Resource 2 slot',
            'date_start': datetime(2025, 1, 6, 8, 0),
            'date_end': datetime(2025, 1, 6, 17, 0),
            'resource_id': resource2.id,
            'allocated_percentage': 100.0,
        })
        rec1.invalidate_recordset(['schedule_overlap_count'])
        rec2.invalidate_recordset(['schedule_overlap_count'])
        self.assertEqual(rec1.schedule_overlap_count, 0)
        self.assertEqual(rec2.schedule_overlap_count, 0)

    # ------------------------------------------------------------------
    # Calendar change recomputation
    # ------------------------------------------------------------------

    def test_calendar_change(self):
        """Changing the resource triggers calendar + hours recomputation."""
        record = self.Model.create({
            'name': 'Calendar change',
            'date_start': datetime(2025, 1, 6, 8, 0),   # Mon 8:00
            'date_end': datetime(2025, 1, 6, 17, 0),     # Mon 17:00
            'resource_id': self.resource.id,
        })
        self.assertEqual(record.allocated_hours, 8.0)
        self.assertEqual(record.resource_calendar_id, self.calendar)

        # Create a resource with a half-day calendar (8:00-12:00 only)
        half_calendar = self.env['resource.calendar'].create({
            'name': 'Half Day Calendar',
            'tz': 'UTC',
            'attendance_ids': [
                (5, 0, 0),  # clear defaults
                (0, 0, {'name': 'Mon AM', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Tue AM', 'dayofweek': '1', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Wed AM', 'dayofweek': '2', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Thu AM', 'dayofweek': '3', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
                (0, 0, {'name': 'Fri AM', 'dayofweek': '4', 'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'}),
            ],
        })
        half_resource = self.env['resource.resource'].create({
            'name': 'Half Day Resource',
            'calendar_id': half_calendar.id,
            'tz': 'UTC',
        })
        # Reassign to a different resource → triggers calendar recompute → hours recompute
        record.resource_id = half_resource
        self.assertEqual(record.resource_calendar_id, half_calendar)
        self.assertEqual(record.allocated_hours, 4.0)
