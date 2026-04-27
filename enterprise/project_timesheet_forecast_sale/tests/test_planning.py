# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta, datetime

from odoo.tests import tagged

from odoo.addons.sale_planning.tests.common import TestCommonSalePlanning


@tagged('post_install', '-at_install')
class TestPlanning(TestCommonSalePlanning):

    def test_copy_previous_week_no_allocated_hours_project(self):
        project = self.env['project.project'].create({'name': 'Planning Project'})
        self.assertEqual(project.allocated_hours, 0)
        PlanningSlot = self.env['planning.slot']
        start = datetime(2019, 6, 25, 8, 0)
        slot = PlanningSlot.create({
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
            'project_id': project.id,
        })
        copy_start = start + timedelta(weeks=1)
        copy_domain = [('start_datetime', '=', copy_start), ('project_id', '=', project.id)]

        self.assertFalse(slot.was_copied)
        copy = PlanningSlot.search(copy_domain)
        self.assertEqual(len(copy), 0, "There should not be any slot at that time before the copy.")
        PlanningSlot.action_copy_previous_week(
            str(copy_start), [
                # dummy domain
                ('start_datetime', '=', True),
                ('end_datetime', '=', True),
            ]
        )
        self.assertTrue(slot.was_copied)
        copy = PlanningSlot.search(copy_domain)
        self.assertEqual(len(copy), 1, "The slot should have been copied as the project has no allocated hours.")
