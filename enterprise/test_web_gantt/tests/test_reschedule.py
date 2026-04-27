# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import freeze_time
from .common import TestWebGantt


@freeze_time(datetime(2021, 4, 1))
class TestWebGanttReschedule(TestWebGantt):

    def test_reschedule_forward(self):
        """ This test purpose is to ensure that the forward rescheduling is properly working. """
        res = self.gantt_reschedule_forward(self.pill_1, self.pill_2)
        self.assert_old_pills_vals(res, 'success', 'Reschedule done successfully.', self.pill_1, self.initial_dates)
        self.assertEqual(
            self.pill_1[self.date_stop_field_name], self.pill_2[self.date_start_field_name],
            'Pill 1 should move forward up to start of Pill 2.'
        )
        self.pill_1.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_not_replanned(self.pill_1, self.initial_dates)

    def test_reschedule_backward(self):
        """ This test purpose is to ensure that the backward rescheduling is properly working. """
        res = self.gantt_reschedule_backward(self.pill_1, self.pill_2)
        self.assert_old_pills_vals(res, 'success', 'Reschedule done successfully.', self.pill_2, self.initial_dates)
        self.assertEqual(
            self.pill_2[self.date_start_field_name], self.pill_1[self.date_stop_field_name],
            'Pill 2 should move backward up to end of Pill 1.'
        )
        self.pill_2.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_not_replanned(self.pill_2, self.initial_dates)

    def test_prevent_action_on_non_dependent_records(self):
        """ This test purpose is to ensure that non-dependent records are not rescheduled. """
        self.pill_3_start_date = self.pill_2_start_date + timedelta(days=1)
        self.pill_3_stop_date = self.pill_3_start_date + timedelta(hours=8)
        self.pill_3 = self.create_pill('Pill 3', self.pill_3_start_date, self.pill_3_stop_date, [self.pill_2.id])
        # Non-dependent records should not be rescheduled.
        with self.assertRaises(ValueError):
            self.gantt_reschedule_forward(self.pill_1, self.pill_3)
        # Non-dependent records should not be rescheduled.
        with self.assertRaises(ValueError):
            self.gantt_reschedule_backward(self.pill_1, self.pill_3)

    def test_not_in_past(self):
        """ This test purpose is to ensure that:
            * Records in the past are not rescheduled.
            * Records are not rescheduled in the past.
            * A notification is returned when trying to reschedule a record in the past.
        """
        a_day_in_the_past = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=1)
        self.pill_in_past = self.create_pill(
            'Pill in past', a_day_in_the_past, a_day_in_the_past + timedelta(hours=8), [self.pill_1.id])
        # Records in the past should not be rescheduled.
        with self.assertRaises(ValueError):
            self.gantt_reschedule_backward(self.pill_in_past, self.pill_1)
        yesterday_midnight = datetime.now().replace(minute=0, second=0, microsecond=0) - timedelta(days=1)
        self.pill_1.write({
            self.date_start_field_name: yesterday_midnight,
            self.date_stop_field_name: yesterday_midnight + timedelta(hours=8),
        })
        result = self.gantt_reschedule_backward(self.pill_1, self.pill_2)
        self.assertEqual(
            self.pill_2[self.date_start_field_name], self.pill_2_start_date,
            'Records should not be rescheduled in the past.'
        )
        self.assert_old_pills_vals(result, "warning", "Pill 2 cannot be scheduled in the past", self.env['test.web.gantt.pill'], {})

    def test_cascade_forward(self):
        """
            [1]->[2]->[3]->[4]
            when moving 2 forward without conflicts, we only move 2 to reduce the distance between 2 and 3,
            ancestors of 2 should not be impacted (1)
            3 and its children should not be impacted
        """
        self.gantt_reschedule_forward(self.pill_2, self.pill_3)
        self.assertEqual(
            (self.pill_1[self.date_start_field_name], self.pill_1[self.date_stop_field_name]),
            (self.pill_1_start_date, self.pill_1_stop_date),
            'Reschedule of Pill 2 should not impact Pill 1.'
        )
        self.assertEqual(
            (self.pill_3[self.date_start_field_name], self.pill_3[self.date_stop_field_name]),
            (self.pill_3_start_date, self.pill_3_stop_date),
            'Reschedule of Pill 2 towards Pill 3 should not have altered Pill 3.'
        )
        self.assertEqual(
            (self.pill_4[self.date_start_field_name], self.pill_4[self.date_stop_field_name]),
            (self.pill_4_start_date, self.pill_4_stop_date),
            'Forward reschedule of Pill 2 should not have an impact on Pill 4.'
        )

    def test_cascade_backward(self):
        """
            [1]->[2]->[3]->[4]
            When the left arrow (move backward arrow) in the dependency between 2 and 3 is clicked,
            as there are no conflicts between them, 3 will be moved backward to reach 2 (the distance will be reduced
            but 3 will stay after 2)

            2 and its ancestors should not be impacted
            children of should not be impacted (4)
        """
        self.gantt_reschedule_backward(self.pill_2, self.pill_3)
        self.assertEqual(
            (self.pill_4[self.date_start_field_name], self.pill_4[self.date_stop_field_name]),
            (self.pill_4_start_date, self.pill_4_stop_date),
            'Reschedule of Pill 3 should not impact Pill 4'
        )
        self.assertEqual(
            (self.pill_2[self.date_start_field_name], self.pill_2[self.date_stop_field_name]),
            (self.pill_2_start_date, self.pill_2_stop_date),
            'Reschedule of Pill 3 towards Pill 2 should not have altered Pill 2.'
        )
        self.assertEqual(
            self.pill_3[self.date_start_field_name], self.pill_2[self.date_stop_field_name]
        )
        self.assertEqual(
            (self.pill_1[self.date_start_field_name], self.pill_1[self.date_stop_field_name]),
            (self.pill_1_start_date, self.pill_1_stop_date),
            'Backward reschedule of Pill 3 should not have an impact on Pill 1.'
        )

    def test_conflicting_cascade_forward(self):
        """
            ┌────────────────────────┐                                       ┌──────────────────────────────────┐
            │pill_2_slave_in_conflict|<---------- -------------------------->|  pill_2_slave_not_in_conflict    |
            └────────────────────────┘          | |                          └──────────────────────────────────┘
            ┌────────────────────────┐      ┌─────────┐     ┌─────────┐      ┌──────────────────────────────────┐
            │ Pill 1                 │ ---> │ Pill 2  │-->  │ Pill 3  │ -->  │ Pill 4                           │
            └────────────────────────┘      └─────────┘     └─────────┘      └──────────────────────────────────┘
            ┌────────────────────────┐                           | |         ┌──────────────────────────────────┐
            │pill_3_slave_in_conflict│<--------------------------- --------->│pill_3_slave_not_in_conflict      │
            └────────────────────────┘                                       └──────────────────────────────────┘

            When moving forward without conflicts, we reduce the distance between trigger_record and related_record and we move
            the children of trigger_record after related_record (only records in conflict, │pill_3_slave_not_in_conflict should not move).
            ancestors should not be impacted
        """
        self.pill_2_slave_in_conflict = self.create_pill(
            'Pill in conflict with Pill 2', self.pill_1_start_date, self.pill_1_stop_date, [self.pill_2.id]
        )
        self.pill_2_slave_not_in_conflict = self.create_pill(
            'Pill not in conflict with Pill 2', self.pill_4_start_date, self.pill_4_stop_date, [self.pill_2.id]
        )
        self.pill_3_slave_in_conflict = self.create_pill(
            'Pill in conflict with Pill 3', self.pill_1_start_date, self.pill_1_stop_date, [self.pill_3.id]
        )
        self.pill_3_slave_not_in_conflict = self.create_pill(
            'Pill not in conflict with Pill 3', self.pill_4_start_date, self.pill_4_stop_date, [self.pill_3.id]
        )
        moved_pills = self.pill_3 | self.pill_3_slave_in_conflict
        initial_dates_deep_copy = dict(self.initial_dates)
        initial_dates_deep_copy[self.pill_3_slave_in_conflict.name] = (self.pill_3_slave_in_conflict.date_start, self.pill_3_slave_in_conflict.date_stop)

        res = self.gantt_reschedule_forward(self.pill_3, self.pill_4)
        self.assert_old_pills_vals(res, 'success', 'Reschedule done successfully.', moved_pills, initial_dates_deep_copy)
        self.assertEqual(
            self.pill_3[self.date_stop_field_name],
            self.pill_4[self.date_start_field_name],
            'pill_3 should have been rescheduled to the start of pill_4'
        )
        self.assertEqual(
            self.pill_3_slave_in_conflict[self.date_start_field_name],
            self.pill_3[self.date_stop_field_name],
            'pill_3_slave_in_conflict should have been rescheduled once pill_3 had been rescheduled.'
        )
        self.assertEqual(
            self.pill_3_slave_not_in_conflict[self.date_start_field_name],
            self.pill_3[self.date_stop_field_name],
            'pill_3_slave_not_in_conflict should not be rescheduled once as it is not in conflict with pill_3.'
        )
        self.assertEqual(
            (self.pill_2[self.date_start_field_name], self.pill_2[self.date_stop_field_name]),
            (self.pill_2_start_date, self.pill_2_stop_date),
            'pill_2 should not be rescheduled.'
        )
        moved_pills.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_not_replanned(moved_pills, initial_dates_deep_copy)

    def test_conflicting_cascade_backward(self):
        """
        ┌──────────────────────────────┐                                       ┌──────────────────────────────────┐
        |pill_2_master_not_in_conflict |----------- ---------------------------|  pill_2_master_in_conflict       |
        └──────────────────────────────┘          | |                          └──────────────────────────────────┘
                                                  v v
        ┌──────────────────────────────┐      ┌─────────┐     ┌─────────┐      ┌──────────────────────────────────┐
        │       Pill 1                 │ ---> │ Pill 2  │-->  │ Pill 3  │ -->  │ Pill 4                           │
        └──────────────────────────────┘      └─────────┘     └─────────┘      └──────────────────────────────────┘
                                                                   ^ ^
        ┌──────────────────────────────┐                           | |         ┌──────────────────────────────────┐
        | pill_3_master_not_in_conflict|---------------------------- ----------|pill_3_master_in_conflict         │
        └──────────────────────────────┘                                       └──────────────────────────────────┘

            When moving backward without conflicts, we reduce the distance between trigger_record and related_record and we move
            the ancestor of trigger_record that are in conflicts before related_record. children should not be impacted
        """
        self.pill_3_master_in_conflict = self.create_pill(
            'Pill in conflict with Pill 3', self.pill_4_start_date, self.pill_4_stop_date
        )
        self.pill_3_master_not_in_conflict = self.create_pill(
            'Pill not in conflict with Pill 3', self.pill_1_start_date, self.pill_1_stop_date
        )
        self.pill_3[self.dependency_field_name] = [
            Command.link(self.pill_3_master_in_conflict.id),
            Command.link(self.pill_3_master_not_in_conflict.id),
        ]
        self.pill_2_master_in_conflict = self.create_pill(
            'Pill in conflict with Pill 2', self.pill_4_start_date, self.pill_4_stop_date
        )
        self.pill_2_master_not_in_conflict = self.create_pill(
            'Pill not in conflict with Pill 2', self.pill_1_start_date, self.pill_1_stop_date
        )
        self.pill_2[self.dependency_field_name] = [
            Command.link(self.pill_2_master_in_conflict.id),
            Command.link(self.pill_2_master_not_in_conflict.id),
        ]
        moved_pills = self.pill_2 | self.pill_2_master_in_conflict
        initial_dates_deep_copy = dict(self.initial_dates)
        initial_dates_deep_copy[self.pill_2_master_in_conflict.name] = (self.pill_2_master_in_conflict.date_start, self.pill_2_master_in_conflict.date_stop)
        res = self.gantt_reschedule_backward(self.pill_1, self.pill_2)
        self.assert_old_pills_vals(res, 'success', 'Reschedule done successfully.', moved_pills, initial_dates_deep_copy)
        self.assertEqual(self.pill_1[self.date_stop_field_name], self.pill_2[self.date_start_field_name])
        self.assertEqual(
            self.pill_2_master_in_conflict[self.date_stop_field_name],
            self.pill_2[self.date_start_field_name],
            'pill_2_master_in_conflict should have been rescheduled once pill_2 had been rescheduled.'
        )
        moved_pills.action_rollback_scheduling(res['old_vals_per_pill_id'])
        self.assert_not_replanned(moved_pills, initial_dates_deep_copy)

    def test_pills2_reschedule_cascading_forward(self):
        """
            This test concerns pills2, when the right arrow is clicked. pill 0 should move ahead of task 8.
            As pills 1, 2, 3 are children of 0, they should be done after it,
            they should also be moved forward
            All the other pills should not move.
        """
        self.gantt_reschedule_forward(self.pills2_8, self.pills2_0)
        self.assert_not_replanned(
            self.pills2_4 | self.pills2_5 | self.pills2_6 | self.pills2_7 | self.pills2_8 | self.pills2_9 |
            self.pills2_10 | self.pills2_11 | self.pills2_12 | self.pills2_13 | self.pills2_14,
            self.initial_dates,
        )

        self.assertEqual(
            self.pills2_0[self.date_start_field_name],
            self.pills2_8[self.date_stop_field_name],
        )
        self.assertEqual(
            self.pills2_1[self.date_start_field_name],
            self.pills2_0[self.date_stop_field_name],
        )
        self.assertEqual(
            self.pills2_2[self.date_start_field_name],
            self.pills2_1[self.date_stop_field_name],
        )
        self.assertEqual(
            self.pills2_2[self.date_start_field_name],
            self.pills2_1[self.date_stop_field_name],
        )

    def test_pills2_reschedule_cascading_backward(self):
        """
            This test concerns pills2, when the left arrow is clicked. pill 8 should be moved behind pill 0
            As pills 4, 6, 5, 7 are ancestors for 8 and should be done before it, they should be moved backward.
            9 and 10 should not be impacted as they are not ancestors of 8.
            All the other pills should not move.
        """
        self.gantt_reschedule_backward(self.pills2_8, self.pills2_0)
        self.assert_not_replanned(
            self.pills2_0 | self.pills2_1 | self.pills2_2 | self.pills2_3 | self.pills2_9 |
            self.pills2_10 | self.pills2_11 | self.pills2_12 | self.pills2_13 | self.pills2_14,
            self.initial_dates,
        )

        self.assertEqual(
            self.pills2_0[self.date_start_field_name],
            self.pills2_8[self.date_stop_field_name],
        )
        self.assertEqual(
            self.pills2_8[self.date_start_field_name],
            self.pills2_7[self.date_stop_field_name],
        )
        self.assertEqual(
            self.pills2_7[self.date_start_field_name],
            self.pills2_6[self.date_stop_field_name],
        )
        self.assertEqual(
            self.pills2_7[self.date_start_field_name],
            self.pills2_5[self.date_stop_field_name],
        )
        self.assertEqual(
            self.pills2_6[self.date_start_field_name],
            self.pills2_4[self.date_stop_field_name],
        )

    def test_dont_move_not_in_conflict(self):
        """
                                      ->[4]
                                      |
                                      ---------<-------
            [1]---------------------------->[2]->[3]--|

            When moving 3 before 4, 2 should also move to avoid creating conflicts, but 1
            should not be moved because with the new dates of 2 and 3, there is no
            conflict created.
        """
        self.pill_4.write({
            self.date_start_field_name: datetime(2021, 4, 27, 8, 0),
            self.date_stop_field_name: datetime(2021, 4, 27, 12, 0),
        })
        self.pill_2.write({
            self.date_start_field_name: datetime(2021, 4, 27, 13, 0),
            self.date_stop_field_name: datetime(2021, 4, 27, 17, 0),
        })
        self.pill_3.write({
            self.date_start_field_name: datetime(2021, 4, 28, 13, 0),
            self.date_stop_field_name: datetime(2021, 4, 28, 18, 0),
        })
        self.gantt_reschedule_backward(self.pill_3, self.pill_4)
        self.assertEqual(
            self.pill_3[self.date_stop_field_name],
            self.pill_4[self.date_start_field_name],
            '3 moved before 4',
        )
        self.assertEqual(
            self.pill_2[self.date_stop_field_name],
            self.pill_3[self.date_start_field_name],
            '2 moved before 3',
        )
        self.assert_not_replanned(self.pills2_1 | self.pills2_4, self.initial_dates)
