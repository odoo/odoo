# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import Command
from .common import TestWebGantt


class TestWebGanttReschedule(TestWebGantt):

    def test_reschedule_forward(self):
        """ This test purpose is to ensure that the forward rescheduling is properly working. """
        self.gantt_reschedule_forward(self.pill_1, self.pill_2)
        self.assertEqual(
            self.pill_1[self.date_stop_field_name], self.pill_2[self.date_start_field_name],
            'Pill 1 should move forward up to start of Pill 2.'
        )

    def test_reschedule_backward(self):
        """ This test purpose is to ensure that the backward rescheduling is properly working. """
        self.gantt_reschedule_backward(self.pill_1, self.pill_2)
        self.assertEqual(
            self.pill_2[self.date_start_field_name], self.pill_1[self.date_stop_field_name],
            'Pill 2 should move backward up to end of Pill 1.'
        )

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
        is_ir_actions_client_type = result and result['type'] and result['type'] == 'ir.actions.client'
        is_notification_tag = result and result['tag'] and result['tag'] == 'display_notification'
        self.assertTrue(
            is_ir_actions_client_type and is_notification_tag,
            'A notification should be returned when trying to reschedule a record in the past.'
        )

    def test_cascade_forward(self):
        """ This test purpose is to ensure that the rescheduling is correctly cascading when performed forward.
            All master records are rescheduled when performing a forward reschedule.
            Non-conflicting slave records are not rescheduled.
        """
        self.gantt_reschedule_forward(self.pill_2, self.pill_3)
        self.assertEqual(
            self.pill_1[self.date_stop_field_name], self.pill_2[self.date_start_field_name],
            'Reschedule of Pill 2 should have cascaded to Pill 1 which should move forward up to start of Pill 2.'
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
        """ This test purpose is to ensure that the rescheduling is correctly cascading when performed backward.
            All slave records are rescheduled when performing a backward reschedule.
            Non-conflicting master records are not rescheduled.
        """
        self.gantt_reschedule_backward(self.pill_2, self.pill_3)
        self.assertEqual(
            self.pill_4[self.date_start_field_name], self.pill_3[self.date_stop_field_name],
            'Reschedule of Pill 3 should have cascaded to Pill 4 which should move backward up to start of Pill 3.'
        )
        self.assertEqual(
            (self.pill_2[self.date_start_field_name], self.pill_2[self.date_stop_field_name]),
            (self.pill_2_start_date, self.pill_2_stop_date),
            'Reschedule of Pill 3 towards Pill 2 should not have altered Pill 2.'
        )
        self.assertEqual(
            (self.pill_1[self.date_start_field_name], self.pill_1[self.date_stop_field_name]),
            (self.pill_1_start_date, self.pill_1_stop_date),
            'Backward reschedule of Pill 3 should not have an impact on Pill 1.'
        )

    def test_conflicting_cascade_forward(self):
        """ This test purpose is to ensure that, when rescheduling forward:
            * All conflicts between a record that would have been rescheduled forward and its slave records are
              resolved.
            * Non-conflicting slave records are not rescheduled.
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
        self.gantt_reschedule_forward(self.pill_3, self.pill_4)
        self.assertEqual(
            self.pill_3_slave_in_conflict[self.date_start_field_name],
            self.pill_3[self.date_stop_field_name],
            'pill_3_slave_in_conflict should have been rescheduled once pill_3 had been rescheduled.'
        )
        self.assertEqual(
            self.pill_3_slave_not_in_conflict[self.date_start_field_name],
            self.pill_4_start_date,
            'pill_3_slave_not_in_conflict should not have been reschedule once pill_3 had been rescheduled.'
        )
        self.assertEqual(
            self.pill_2_slave_in_conflict[self.date_start_field_name],
            self.pill_2[self.date_stop_field_name],
            'pill_2_slave_in_conflict should have been rescheduled once pill_2 had been rescheduled.'
        )
        self.assertEqual(
            self.pill_2_slave_not_in_conflict[self.date_start_field_name],
            self.pill_4_start_date,
            'pill_2_slave_not_in_conflict should not have been reschedule once pill_2 had been rescheduled.'
        )

    def test_conflicting_cascade_backward(self):
        """ This test purpose is to ensure that, when rescheduling backward:
            * All conflicts between a record that would have been rescheduled backward and its master records are
              resolved.
            * Non-conflicting master records are not rescheduled.
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
        self.gantt_reschedule_backward(self.pill_1, self.pill_2)
        self.assertEqual(
            self.pill_2_master_in_conflict[self.date_stop_field_name],
            self.pill_2[self.date_start_field_name],
            'pill_2_master_in_conflict should have been rescheduled once pill_2 had been rescheduled.'
        )
        self.assertEqual(
            self.pill_2_master_not_in_conflict[self.date_stop_field_name],
            self.pill_1_stop_date,
            'pill_2_master_not_in_conflict should not have been reschedule once pill_2 had been rescheduled.'
        )
        self.assertEqual(
            self.pill_3_master_in_conflict[self.date_stop_field_name],
            self.pill_3[self.date_start_field_name],
            'pill_3_master_in_conflict should have been rescheduled once pill_3 had been rescheduled.'
        )
        self.assertEqual(
            self.pill_3_master_not_in_conflict[self.date_stop_field_name],
            self.pill_1_stop_date,
            'pill_3_master_not_in_conflict should not have been reschedule once pill_3 had been rescheduled.'
        )

    def check_dependencies(self):
        """ Assert that each pill start_date is later than the ones of its master pills. """
        for pill in self.pills:
            for master_pill in pill[self.dependency_field_name]:
                self.assertTrue(master_pill[self.date_start_field_name] < pill[self.date_start_field_name])

    def get_start_date_for_pill(self, pill):
        """ Returns the start date for the provided pill.
            :param pill: The pill the start date has to be returned for.
        """
        if pill == self.pill_1:
            return self.pill_1_start_date
        if pill == self.pill_2:
            return self.pill_2_start_date
        if pill == self.pill_3:
            return self.pill_3_start_date
        if pill == self.pill_4:
            return self.pill_4_start_date
        if pill == self.pill_5:
            return self.pill_5_start_date
        if pill == self.pill_6:
            return self.pill_6_start_date
        return False

    def check_pills_have_not_been_rescheduled(self, pills, trigger_pill):
        """ Checks that pills, other than trigger_pill, have not been rescheduled.
            :param pills: Pills to check.
            :param trigger_pill: Pill that originated the rescheduling.
        """
        pill_number = pills.index(trigger_pill) + 1
        for pill in pills:
            if pill != trigger_pill:
                self.assertEqual(
                    pill[self.date_start_field_name], self.get_start_date_for_pill(pill),
                    f'Pill {pill_number} should hot have been rescheduled as the algorithm should not have '
                    f'solve the loop.'
                )

    def non_straight_dependency_alert_1_test(self, trigger_pill_number):
        """ Ensures that situation as described bellow return a notification and only first move is performed
            as the resolution is not supported. Instead of risking altering the data with remaining conflicts
            (as the number of situation and crossed links can be unlimited), we just rollback all changes as
            soon as we detect that we have a `loop` (not meaning circular dependency).

               ---------------- 6
             /                /
            1 - 2 - 3 - 4 - 5

               with a 7 (linked to the pill corresponding to trigger_pill_number)

        """
        self.pill_5_start_date = self.pill_4_start_date + timedelta(days=1)
        self.pill_5_stop_date = self.pill_5_start_date + timedelta(hours=8)
        self.pill_5 = self.create_pill('Pill 5', self.pill_5_start_date, self.pill_5_stop_date, [self.pill_4.id])
        self.pill_6_start_date = self.pill_5_start_date + timedelta(days=1)
        self.pill_6_stop_date = self.pill_6_start_date + timedelta(hours=8)
        self.pill_6 = self.create_pill(
            'Pill 6', self.pill_6_start_date, self.pill_6_stop_date, [self.pill_5.id, self.pill_1.id]
        )
        pills = [self.pill_1, self.pill_2, self.pill_3, self.pill_4, self.pill_5, self.pill_6]
        trigger_pill = pills[trigger_pill_number - 1]
        self.pill_7_start_date = self.pill_6_start_date + timedelta(days=1)
        self.pill_7_stop_date = self.pill_7_start_date + timedelta(hours=8)
        self.pill_7 = self.create_pill('Pill 7', self.pill_7_start_date, self.pill_7_stop_date, [trigger_pill.id])
        result = self.gantt_reschedule_forward(trigger_pill, self.pill_7)
        self.assertTrue(
            result and result['type'] and result['type'] == 'ir.actions.client',
            'The rescheduling should return a notification when the algorithm cannot solve the loop.'
        )
        self.assertEqual(
            trigger_pill[self.date_stop_field_name], self.pill_7[self.date_start_field_name],
            'The first move should be saved when the algorithm cannot solve the loop.'
        )
        self.check_pills_have_not_been_rescheduled(pills, trigger_pill)

    def test_non_straight_dependency_alert_1_a(self):
        """ Ensures that rescheduling 1 towards 7, in the situation as described bellow, returns a notification and
            only first move is performed as the resolution is not supported.

                  ________________________________ 7
                /                                                   5 - 6
               ---------------- 6                                     /         Placing 1, 2 and 6, 3 and 5,
             /                /                               =>    1 - 7       with next step being placing 4
            1 - 2 - 3 - 4 - 5                                         \
                                                                       2 - 3

        """
        self.non_straight_dependency_alert_1_test(1)

    def test_non_straight_dependency_alert_1_c(self):
        """ Ensures that rescheduling 6 towards 7, in the situation as described bellow, returns a notification and
            only first move is performed as the resolution is not supported.

                                    __________ 7
                                  /                                        2   7
               ---------------- 6                                        /   /       Placing 6, 1 and 5, 2 and 4,
             /                /                               =>       1 - 6         with next step being placing 3
            1 - 2 - 3 - 4 - 5                                            /
                                                                   4 - 5

        """
        self.non_straight_dependency_alert_1_test(6)

    def non_straight_dependency_alert_2_test(self, trigger_pill_number):
        """ Ensures that situation as described bellow raises a Validation error as the resolution is not supported.
            Instead of risking altering the data with remaining conflicts (as the number of situation and crossed
            links can be unlimited), we just rollback all changes as soon as we detect that we have a `loop`
            (not meaning circular dependency).

            THIS TEST IS NOT A DUPLICATE OF test_non_straight_dependency_alert_1_* !!! The current algorythm need to
            be tested with both an odd and an even number of elements in a `loop`.

               -----------5
             /           /
            1 - 2 - 3 - 4

               with a 7 (linked to the pill corresponding to trigger_pill_number)

            Notice that if 3 is linked, the resolution will be performed smoothly => 3 -> (2, 4) => (1, 5) without
            conflicts.

        """
        self.pill_5_start_date = self.pill_4_start_date + timedelta(days=1)
        self.pill_5_stop_date = self.pill_5_start_date + timedelta(hours=8)
        self.pill_5 = self.create_pill(
            'Pill 5', self.pill_5_start_date, self.pill_5_stop_date, [self.pill_4.id, self.pill_1.id]
        )
        pills = [self.pill_1, self.pill_2, self.pill_3, self.pill_4, self.pill_5]
        trigger_pill = pills[trigger_pill_number - 1]
        self.pill_7_start_date = self.pill_5_start_date + timedelta(weeks=1)
        self.pill_7_stop_date = self.pill_7_start_date + timedelta(hours=8)
        self.pill_7 = self.create_pill('Pill 7', self.pill_7_start_date, self.pill_7_stop_date, [trigger_pill.id])
        result = self.gantt_reschedule_forward(trigger_pill, self.pill_7)
        self.assertTrue(
            result and result['type'] and result['type'] == 'ir.actions.client',
            'The rescheduling should return a notification when the algorithm cannot solve the loop.'
        )
        self.assertEqual(
            trigger_pill[self.date_stop_field_name], self.pill_7[self.date_start_field_name],
            'The first move should be saved when the algorithm cannot solve the loop.'
        )
        self.check_pills_have_not_been_rescheduled(pills, trigger_pill)

    def test_non_straight_dependency_alert_2_a(self):
        """ Ensures that rescheduling 1 towards 7, in the situation as described bellow, returns a notification and
            only first move is performed as the resolution is not supported.

                  ______________________ 7
                /                                                   4 - 5       Placing 1, 2 and 5, 3 and 4,
               -------------5                                         /         with next step being replacing 3 and 4
             /            /                                   =>    1 - 7       as in conflict.
            1 - 2 - 3 - 4                                             \
                                                                       2 - 3

        """
        self.non_straight_dependency_alert_2_test(1)

    def test_non_straight_dependency_alert_2_b(self):
        """ Ensures that rescheduling 5 towards 7, in the situation as described bellow, returns a notification and
            only first move is performed as the resolution is not supported.

                                ______________ 7
                              /                                            2   7
               ------------ 5                                            /   /     Placing 5, 1 and 4, 2 and 3,
             /            /                                   =>       1 - 5       with next step being placing 2 and 3
            1 - 2 - 3 - 4                                                /         as in conflict.
                                                                   3 - 4

        """
        self.non_straight_dependency_alert_2_test(5)

    def test_direction_shift_when_in_conflict(self):
        """ This test purpose is to ensure that the correct record is moved when rescheduling forward / backward and
            depending on the fact the records are in conflicts or not (master_record stop_date_field is later than the
            slave_record start_date_field means they are in conflict).
        """
        self.gantt_reschedule_forward(self.pill_1, self.pill_2)
        self.assertGreater(
            self.pill_1[self.date_start_field_name], self.pill_1_start_date,
            'Pill 1 should have been rescheduled forward.'
        )
        self.assertEqual(
            self.pill_2[self.date_start_field_name], self.pill_2_start_date, 'Pill 2 should not have been rescheduled.'
        )
        self.gantt_reschedule_backward(self.pill_3, self.pill_4)
        self.assertLess(
            self.pill_4[self.date_start_field_name], self.pill_4_start_date,
            'Pill 4 should have been rescheduled backward.'
        )
        self.assertEqual(
            self.pill_3[self.date_start_field_name], self.pill_3_start_date, 'Pill 3 should not have been rescheduled.'
        )
        self.pill_1_master_in_conflict_start_date = self.pill_1_start_date + timedelta(days=1)
        self.pill_1_master_in_conflict = self.create_pill(
            'Pill in conflict with Pill 1',
            self.pill_1_master_in_conflict_start_date, self.pill_1_master_in_conflict_start_date + timedelta(hours=8)
        )
        self.pill_1.write({self.dependency_field_name: [Command.link(self.pill_1_master_in_conflict.id)]})
        self.gantt_reschedule_forward(self.pill_1_master_in_conflict, self.pill_1)
        self.assertGreater(
            self.pill_1[self.date_start_field_name], self.pill_1_start_date,
            'Pill 1 should have been rescheduled.'
        )
        self.assertEqual(
            self.pill_1_master_in_conflict[self.date_start_field_name], self.pill_2_start_date,
            'Pill in conflict with Pill 1 should not have been rescheduled.'
        )
        self.pill_4_slave_in_conflict_start_date = self.pill_4_start_date - timedelta(days=1)
        self.pill_4_slave_in_conflict = self.create_pill(
            'Pill in conflict with Pill 4',
            self.pill_4_slave_in_conflict_start_date, self.pill_4_slave_in_conflict_start_date + timedelta(hours=8),
            [self.pill_4.id]
        )
        self.gantt_reschedule_backward(self.pill_4, self.pill_4_slave_in_conflict)
        self.assertLess(
            self.pill_4[self.date_start_field_name], self.pill_4_start_date,
            'Pill 4 should have been rescheduled.'
        )
        self.assertEqual(
            self.pill_4_slave_in_conflict[self.date_start_field_name], self.pill_4_slave_in_conflict_start_date,
            'Pill in conflict with Pill 4 should not have been rescheduled.'
        )
