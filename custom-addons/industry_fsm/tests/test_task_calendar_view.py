from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tests import Form

from odoo.addons.project.tests.test_project_base import TestProjectCommon


class TestTaskCalendarView(TestProjectCommon):

    def test_simulate_task_creation_from_calendar(self):
        """
            Create a task in the task form 2, form called from the calendar view, and apply the same context as the calendar would.
        """
        now = datetime.combine(datetime.now(), datetime.min.time())
        default_date_planned_start = now + relativedelta(days=3, hour=7)
        default_date_deadline = now + relativedelta(days=3, hour=19)
        calendar_ctx = {'default_date_planned_start': default_date_planned_start, 'default_date_deadline': default_date_deadline}

        task_form = Form(self.env['project.task'].with_context(calendar_ctx), view="project.view_task_form2")
        task_form.name = 'Test Task 1'
        task_form.project_id = self.project_pigs
        task_form.planned_date_begin = now
        task_form.date_deadline = now + relativedelta(days=1)
        task_form.partner_id = self.partner_1
        task_form.user_ids = self.env.user
        task = task_form.save()

        self.assertEqual(task.planned_date_begin, now)
