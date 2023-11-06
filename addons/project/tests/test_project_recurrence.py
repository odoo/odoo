# -*- coding: utf-8 -*-


from odoo.tests.common import TransactionCase, Form
from odoo.exceptions import ValidationError
from odoo import fields

from datetime import date, datetime
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU
from freezegun import freeze_time


class TestProjectrecurrence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestProjectrecurrence, cls).setUpClass()

        cls.env.user.groups_id += cls.env.ref('project.group_project_recurring_tasks')

        cls.stage_a = cls.env['project.task.type'].create({'name': 'a'})
        cls.stage_b = cls.env['project.task.type'].create({'name': 'b'})
        cls.project_recurring = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Recurring',
            'allow_recurring_tasks': True,
            'type_ids': [
                (4, cls.stage_a.id),
                (4, cls.stage_b.id),
            ]
        })

    def set_task_create_date(self, task_id, create_date):
        self.env.cr.execute("UPDATE project_task SET create_date=%s WHERE id=%s", (create_date, task_id))

    def test_recurrence_simple(self):
        with freeze_time("2020-02-01"):
            with Form(self.env['project.task']) as form:
                form.name = 'test recurring task'
                form.project_id = self.project_recurring

                form.recurring_task = True
                form.repeat_interval = 5
                form.repeat_unit = 'month'
                form.repeat_type = 'after'
                form.repeat_number = 10
                form.repeat_on_month = 'date'
                form.repeat_day = '31'
            task = form.save()
            self.assertTrue(bool(task.recurrence_id), 'should create a recurrence')

            task.write(dict(repeat_interval=2, repeat_number=11))
            self.assertEqual(task.recurrence_id.repeat_interval, 2, 'recurrence should be updated')
            self.assertEqual(task.recurrence_id.repeat_number, 11, 'recurrence should be updated')
            self.assertEqual(task.recurrence_id.recurrence_left, 11)
            self.assertEqual(task.recurrence_id.next_recurrence_date, date(2020, 2, 29))

            task.recurring_task = False
            self.assertFalse(bool(task.recurrence_id), 'the recurrence should be deleted')

    def test_recurrence_cron_repeat_after(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time("2020-01-01"):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.description = 'my super recurring task bla bla bla'
            form.project_id = self.project_recurring
            form.date_deadline = datetime(2020, 2, 1)

            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = 'month'
            form.repeat_type = 'after'
            form.repeat_number = 2
            form.repeat_on_month = 'date'
            form.repeat_day = '15'
            task = form.save()
            task.planned_hours = 2

            self.assertEqual(task.recurrence_id.next_recurrence_date, date(2020, 1, 15))
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')
            self.assertEqual(task.recurrence_id.recurrence_left, 2)

        with freeze_time("2020-01-15"):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)
            self.assertEqual(task.recurrence_id.recurrence_left, 1)

        with freeze_time("2020-02-15"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)
            self.assertEqual(task.recurrence_id.recurrence_left, 0)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)
            self.assertEqual(task.recurrence_id.recurrence_left, 0)


        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 3)

        self.assertTrue(bool(tasks[2].date_deadline))
        self.assertFalse(tasks[1].date_deadline, "Deadline should not be copied")

        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(tasks[0][f] == tasks[1][f] == tasks[2][f], "Field %s should have been copied" % f)

    def test_recurrence_cron_repeat_until(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time("2020-01-01"):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.description = 'my super recurring task bla bla bla'
            form.project_id = self.project_recurring
            form.date_deadline = datetime(2020, 2, 1)

            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = 'month'
            form.repeat_type = 'until'
            form.repeat_until = date(2020, 2, 20)
            form.repeat_on_month = 'date'
            form.repeat_day = '15'
            task = form.save()
            task.planned_hours = 2

            self.assertEqual(task.recurrence_id.next_recurrence_date, date(2020, 1, 15))
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time("2020-01-15"):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-02-15"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 3)

        self.assertTrue(bool(tasks[2].date_deadline))
        self.assertFalse(tasks[1].date_deadline, "Deadline should not be copied")

        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(tasks[0][f] == tasks[1][f] == tasks[2][f], "Field %s should have been copied" % f)

    def test_recurrence_cron_repeat_forever(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time("2020-01-01"):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.description = 'my super recurring task bla bla bla'
            form.project_id = self.project_recurring
            form.date_deadline = datetime(2020, 2, 1)

            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = 'month'
            form.repeat_type = 'forever'
            form.repeat_on_month = 'date'
            form.repeat_day = '15'
            task = form.save()
            task.planned_hours = 2

            self.assertEqual(task.recurrence_id.next_recurrence_date, date(2020, 1, 15))
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time("2020-01-15"):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-02-15"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time("2020-02-16"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time("2020-02-17"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time("2020-02-17"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time("2020-03-15"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 4)

        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 4)

        self.assertTrue(bool(tasks[3].date_deadline))
        self.assertFalse(tasks[1].date_deadline, "Deadline should not be copied")

        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(
                tasks[0][f] == tasks[1][f] == tasks[2][f] == tasks[3][f],
                "Field %s should have been copied" % f)

    def test_recurrence_update_task(self):
        with freeze_time("2020-01-01"):
            task = self.env['project.task'].create({
                    'name': 'test recurring task',
                    'project_id': self.project_recurring.id,
                    'recurring_task': True,
                    'repeat_interval': 1,
                    'repeat_unit': 'week',
                    'repeat_type': 'after',
                    'repeat_number': 2,
                    'mon': True,
                })

        with freeze_time("2020-01-06"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()

        with freeze_time("2020-01-13"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()

        task_c, task_b, task_a = self.env['project.task'].search([('project_id', '=', self.project_recurring.id)])

        self.set_task_create_date(task_a.id, datetime(2020, 1, 1))
        self.set_task_create_date(task_b.id, datetime(2020, 1, 6))
        self.set_task_create_date(task_c.id, datetime(2020, 1, 13))
        (task_a+task_b+task_c).invalidate_model()

        task_c.write({
            'name': 'my super updated task',
            'recurrence_update': 'all',
        })

        self.assertEqual(task_a.name, 'my super updated task')
        self.assertEqual(task_b.name, 'my super updated task')
        self.assertEqual(task_c.name, 'my super updated task')

        task_a.write({
            'name': 'don\'t you dare change my title',
            'recurrence_update': 'this',
        })

        self.assertEqual(task_a.name, 'don\'t you dare change my title')
        self.assertEqual(task_b.name, 'my super updated task')
        self.assertEqual(task_c.name, 'my super updated task')

        task_b.write({
            'description': 'hello!',
            'recurrence_update': 'subsequent',
        })

        self.assertEqual(task_a.description, False)
        self.assertEqual(task_b.description, '<p>hello!</p>')
        self.assertEqual(task_c.description, '<p>hello!</p>')

    def test_recurrence_fields_visibility(self):
        form = Form(self.env['project.task'])

        form.name = 'test recurring task'
        form.project_id = self.project_recurring
        form.recurring_task = True

        form.repeat_unit = 'week'
        self.assertTrue(form.repeat_show_dow)
        self.assertFalse(form.repeat_show_day)
        self.assertFalse(form.repeat_show_week)
        self.assertFalse(form.repeat_show_month)

        form.repeat_unit = 'month'
        form.repeat_on_month = 'date'
        self.assertFalse(form.repeat_show_dow)
        self.assertTrue(form.repeat_show_day)
        self.assertFalse(form.repeat_show_week)
        self.assertFalse(form.repeat_show_month)

        form.repeat_unit = 'month'
        form.repeat_on_month = 'day'
        self.assertFalse(form.repeat_show_dow)
        self.assertFalse(form.repeat_show_day)
        self.assertTrue(form.repeat_show_week)
        self.assertFalse(form.repeat_show_month)

        form.repeat_unit = 'year'
        form.repeat_on_year = 'date'
        self.assertFalse(form.repeat_show_dow)
        self.assertTrue(form.repeat_show_day)
        self.assertFalse(form.repeat_show_week)
        self.assertTrue(form.repeat_show_month)

        form.repeat_unit = 'year'
        form.repeat_on_year = 'day'
        self.assertFalse(form.repeat_show_dow)
        self.assertFalse(form.repeat_show_day)
        self.assertTrue(form.repeat_show_week)
        self.assertTrue(form.repeat_show_month)

        form.recurring_task = False
        self.assertFalse(form.repeat_show_dow)
        self.assertFalse(form.repeat_show_day)
        self.assertFalse(form.repeat_show_week)
        self.assertFalse(form.repeat_show_month)

    def test_recurrence_week_day(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env['project.task'].create({
                'name': 'test recurring task',
                'project_id': self.project_recurring.id,
                'recurring_task': True,
                'repeat_interval': 1,
                'repeat_unit': 'week',
                'repeat_type': 'after',
                'repeat_number': 2,
                'mon': False,
                'tue': False,
                'wed': False,
                'thu': False,
                'fri': False,
                'sat': False,
                'sun': False,
            })

    def test_recurrence_next_dates_week(self):
        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2020, 1, 1),
            repeat_interval=1,
            repeat_unit='week',
            repeat_type=False,
            repeat_until=False,
            repeat_on_month=False,
            repeat_on_year=False,
            weekdays=False,
            repeat_day=False,
            repeat_week=False,
            repeat_month=False,
            count=5)

        self.assertEqual(dates[0], datetime(2020, 1, 6, 0, 0))
        self.assertEqual(dates[1], datetime(2020, 1, 13, 0, 0))
        self.assertEqual(dates[2], datetime(2020, 1, 20, 0, 0))
        self.assertEqual(dates[3], datetime(2020, 1, 27, 0, 0))
        self.assertEqual(dates[4], datetime(2020, 2, 3, 0, 0))

        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2020, 1, 1),
            repeat_interval=3,
            repeat_unit='week',
            repeat_type='until',
            repeat_until=date(2020, 2, 1),
            repeat_on_month=False,
            repeat_on_year=False,
            weekdays=[MO, FR],
            repeat_day=False,
            repeat_week=False,
            repeat_month=False,
            count=100)

        self.assertEqual(len(dates), 3)
        self.assertEqual(dates[0], datetime(2020, 1, 3, 0, 0))
        self.assertEqual(dates[1], datetime(2020, 1, 20, 0, 0))
        self.assertEqual(dates[2], datetime(2020, 1, 24, 0, 0))

    def test_recurrence_next_dates_month(self):
        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2020, 1, 15),
            repeat_interval=1,
            repeat_unit='month',
            repeat_type=False, # Forever
            repeat_until=False,
            repeat_on_month='date',
            repeat_on_year=False,
            weekdays=False,
            repeat_day=31,
            repeat_week=False,
            repeat_month=False,
            count=12)

        # should take the last day of each month
        self.assertEqual(dates[0], date(2020, 1, 31))
        self.assertEqual(dates[1], date(2020, 2, 29))
        self.assertEqual(dates[2], date(2020, 3, 31))
        self.assertEqual(dates[3], date(2020, 4, 30))
        self.assertEqual(dates[4], date(2020, 5, 31))
        self.assertEqual(dates[5], date(2020, 6, 30))
        self.assertEqual(dates[6], date(2020, 7, 31))
        self.assertEqual(dates[7], date(2020, 8, 31))
        self.assertEqual(dates[8], date(2020, 9, 30))
        self.assertEqual(dates[9], date(2020, 10, 31))
        self.assertEqual(dates[10], date(2020, 11, 30))
        self.assertEqual(dates[11], date(2020, 12, 31))

        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2020, 2, 20),
            repeat_interval=3,
            repeat_unit='month',
            repeat_type=False, # Forever
            repeat_until=False,
            repeat_on_month='date',
            repeat_on_year=False,
            weekdays=False,
            repeat_day=29,
            repeat_week=False,
            repeat_month=False,
            count=5)

        self.assertEqual(dates[0], date(2020, 2, 29))
        self.assertEqual(dates[1], date(2020, 5, 29))
        self.assertEqual(dates[2], date(2020, 8, 29))
        self.assertEqual(dates[3], date(2020, 11, 29))
        self.assertEqual(dates[4], date(2021, 2, 28))

        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2020, 1, 10),
            repeat_interval=1,
            repeat_unit='month',
            repeat_type='until',
            repeat_until=datetime(2020, 5, 31),
            repeat_on_month='day',
            repeat_on_year=False,
            weekdays=[SA(4), ], # 4th Saturday
            repeat_day=29,
            repeat_week=False,
            repeat_month=False,
            count=6)

        self.assertEqual(len(dates), 5)
        self.assertEqual(dates[0], datetime(2020, 1, 25))
        self.assertEqual(dates[1], datetime(2020, 2, 22))
        self.assertEqual(dates[2], datetime(2020, 3, 28))
        self.assertEqual(dates[3], datetime(2020, 4, 25))
        self.assertEqual(dates[4], datetime(2020, 5, 23))

        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=datetime(2020, 1, 10),
            repeat_interval=6, # twice a year
            repeat_unit='month',
            repeat_type='until',
            repeat_until=datetime(2021, 1, 11),
            repeat_on_month='date',
            repeat_on_year=False,
            weekdays=[TH(+1)],
            repeat_day='3', # the 3rd of the month
            repeat_week=False,
            repeat_month=False,
            count=1)

        self.assertEqual(len(dates), 2)
        self.assertEqual(dates[0], datetime(2020, 7, 3))
        self.assertEqual(dates[1], datetime(2021, 1, 3))

        # Should generate a date at the last day of the current month
        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2022, 2, 26),
            repeat_interval=1,
            repeat_unit='month',
            repeat_type='until',
            repeat_until=date(2022, 2, 28),
            repeat_on_month='date',
            repeat_on_year=False,
            weekdays=False,
            repeat_day=31,
            repeat_week=False,
            repeat_month=False,
            count=5)

        self.assertEqual(len(dates), 1)
        self.assertEqual(dates[0], date(2022, 2, 28))

        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2022, 11, 26),
            repeat_interval=3,
            repeat_unit='month',
            repeat_type='until',
            repeat_until=date(2024, 2, 29),
            repeat_on_month='date',
            repeat_on_year=False,
            weekdays=False,
            repeat_day=25,
            repeat_week=False,
            repeat_month=False,
            count=5)

        self.assertEqual(len(dates), 5)
        self.assertEqual(dates[0], date(2023, 2, 25))
        self.assertEqual(dates[1], date(2023, 5, 25))
        self.assertEqual(dates[2], date(2023, 8, 25))
        self.assertEqual(dates[3], date(2023, 11, 25))
        self.assertEqual(dates[4], date(2024, 2, 25))

        # Use the exact same parameters than the previous test but with a repeat_day that is not passed yet
        # So we generate an additional date in the current month
        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2022, 11, 26),
            repeat_interval=3,
            repeat_unit='month',
            repeat_type='until',
            repeat_until=date(2024, 2, 29),
            repeat_on_month='date',
            repeat_on_year=False,
            weekdays=False,
            repeat_day=31,
            repeat_week=False,
            repeat_month=False,
            count=5)

        self.assertEqual(len(dates), 6)
        self.assertEqual(dates[0], date(2022, 11, 30))
        self.assertEqual(dates[1], date(2023, 2, 28))
        self.assertEqual(dates[2], date(2023, 5, 31))
        self.assertEqual(dates[3], date(2023, 8, 31))
        self.assertEqual(dates[4], date(2023, 11, 30))
        self.assertEqual(dates[5], date(2024, 2, 29))

    def test_recurrence_next_dates_year(self):
        dates = self.env['project.task.recurrence']._get_next_recurring_dates(
            date_start=date(2020, 12, 1),
            repeat_interval=1,
            repeat_unit='year',
            repeat_type='until',
            repeat_until=datetime(2026, 1, 1),
            repeat_on_month=False,
            repeat_on_year='date',
            weekdays=False,
            repeat_day=31,
            repeat_week=False,
            repeat_month='november',
            count=10)

        self.assertEqual(len(dates), 5)
        self.assertEqual(dates[0], datetime(2021, 11, 30))
        self.assertEqual(dates[1], datetime(2022, 11, 30))
        self.assertEqual(dates[2], datetime(2023, 11, 30))
        self.assertEqual(dates[3], datetime(2024, 11, 30))
        self.assertEqual(dates[4], datetime(2025, 11, 30))

    def test_recurrence_cron_repeat_after_subtasks(self):

        def get_task_and_subtask_counts(domain):
            tasks = self.env['project.task'].search(domain)
            return tasks, len(tasks), len(tasks.filtered('parent_id'))

        # Required for `child_ids` to be visible in the view
        # {'invisible': [('allow_subtasks', '=', False)]}
        self.project_recurring.allow_subtasks = True
        parent_task = self.env['project.task'].create({
            'name': 'Parent Task',
            'project_id': self.project_recurring.id
        })
        child_task = self.env['project.task'].create({
            'name': 'Child Task',
            'parent_id': parent_task.id,
        })
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time("2020-01-01"):
            with Form(child_task.with_context({'tracking_disable': True})) as form:
                form.description = 'my super recurring task bla bla bla'
                form.date_deadline = datetime(2020, 2, 1)
                form.display_project_id = parent_task.project_id

                form.recurring_task = True
                form.repeat_interval = 1
                form.repeat_unit = 'month'
                form.repeat_type = 'after'
                form.repeat_number = 2
                form.repeat_on_month = 'date'
                form.repeat_day = '15'
            subtask = form.save()
            subtask.planned_hours = 2

            self.assertEqual(subtask.recurrence_id.next_recurrence_date, date(2020, 1, 15))
            project_tasks, project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 2)
            self.assertEqual(project_subtask_count, 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 2, 'no extra task should be created')
            self.assertEqual(subtask.recurrence_id.recurrence_left, 2)
            for task in project_tasks:
                self.assertEqual(task.display_project_id, parent_task.project_id, "All tasks should have a display project id set")

        with freeze_time("2020-01-15"):
            project_tasks, project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 2)
            self.assertEqual(project_subtask_count, 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            project_tasks, project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 3)
            self.assertEqual(project_subtask_count, 2)
            self.assertEqual(subtask.recurrence_id.recurrence_left, 1)
            for task in project_tasks:
                self.assertEqual(task.display_project_id, parent_task.project_id, "All tasks should have a display project id set")

        with freeze_time("2020-02-15"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            project_tasks, project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 4)
            self.assertEqual(project_subtask_count, 3)
            self.assertEqual(subtask.recurrence_id.recurrence_left, 0)
            for task in project_tasks:
                self.assertEqual(task.display_project_id, parent_task.project_id, "All tasks should have a display project id set")
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            _, project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 4)
            self.assertEqual(project_subtask_count, 3)
            self.assertEqual(subtask.recurrence_id.recurrence_left, 0)

        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 4)

        self.assertTrue(bool(tasks[2].date_deadline))
        self.assertFalse(tasks[1].date_deadline, "Deadline should not be copied")

        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(tasks[0][f] == tasks[1][f] == tasks[2][f], "Field %s should have been copied" % f)

    def test_recurrence_cron_repeat_after_subsubtasks(self):
        """
        Tests how the recurrence is working when a task has subtasks that have recurrence too
        We have at the beginning:
        index	Task name	            Recurrent	                        parent
            0	Parent Task	            no	                                no
            1	Subtask 1	            no                                  Parent task
            2	Subtask 2 	            Montly, 15, for 2 tasks 	        Parent task
            3	Grand child task 1	    Daily, 5 tasks                      Subtask 2 that has recurrence
            4	Grand child task 2	    no                                  Subtask 2 that has recurrence
            5	Grand child task 3	    no                                  Grand child task 2
            6	Grand child task 4	    no                                  Grand child task 3
            7	Grand child task 5	    no                                  Grand child task 4
        1) After 5 days (including today), there will be 5 occurences of *task index 3*.
        2) After next 15th of the month, there will be 2 occurences of *task index 2* and a *copy of tasks 3, 4, 5, 6* (not 7)
        3) 5 days afterwards, there will be 5 occurences of the *copy of task index 3*
        4) The 15th of the next month, there won't be any other new occurence since all recurrences have been consumed.
        """

        def get_task_and_subtask_counts(domain):
            tasks = self.env['project.task'].search(domain)
            return len(tasks), len(tasks.filtered('parent_id'))

        # Phase 0 : Initialize test case
        # Required for `child_ids` to be visible in the view
        # {'invisible': [('allow_subtasks', '=', False)]}
        self.project_recurring.allow_subtasks = True
        parent_task = self.env['project.task'].create({
            'name': 'Parent Task',
            'project_id': self.project_recurring.id
        })
        domain = [('project_id', '=', self.project_recurring.id)]
        child_task_1, child_task_2_recurrence = self.env['project.task'].create([
            {'name': 'Child task 1'},
            {'name': 'Child task 2 that have recurrence'},
        ])
        with Form(parent_task.with_context({'tracking_disable': True})) as task_form:
            task_form.child_ids.add(child_task_1)
            task_form.child_ids.add(child_task_2_recurrence)

        grand_child_task_1 = self.env['project.task'].create({
            'name': 'Grandchild task 1 (recurrent)',
        })
        grand_child_task_2_recurrence = self.env['project.task'].create({
            'name': 'Grandchild task 2',
        })
        with freeze_time("2020-01-01"):
            recurrent_subtask = parent_task.child_ids[0]
            with Form(recurrent_subtask.with_context(tracking_disable=True)) as task_form:
                task_form.recurring_task = True
                task_form.repeat_interval = 1
                task_form.repeat_unit = 'month'
                task_form.repeat_type = 'after'
                task_form.repeat_number = 1
                task_form.repeat_on_month = 'date'
                task_form.repeat_day = '15'
                task_form.date_deadline = datetime(2020, 2, 1)
                task_form.child_ids.add(grand_child_task_1)
                task_form.child_ids.add(grand_child_task_2_recurrence)
            # configure recurring subtask
            recurrent_subsubtask = recurrent_subtask.child_ids.filtered(lambda t: t.name == 'Grandchild task 1 (recurrent)')
            non_recurrent_subsubtask = recurrent_subtask.child_ids.filtered(lambda t: t.name == 'Grandchild task 2')
            with Form(recurrent_subsubtask.with_context(tracking_disable=True)) as subtask_form:
                subtask_form.recurring_task = True
                subtask_form.repeat_interval = 1
                subtask_form.repeat_unit = 'day'
                subtask_form.repeat_type = 'after'
                subtask_form.repeat_number = 4
                subtask_form.date_deadline = datetime(2020, 2, 3)

            grand_child_task_3, grand_child_task_4, grand_child_task_5 = self.env['project.task'].create([
                {'name': 'Grandchild task 3'},
                {'name': 'Grandchild task 4'},
                {'name': 'Grandchild task 5'},
            ])
            # create non-recurring grandchild subtasks
            with Form(non_recurrent_subsubtask.with_context(tracking_disable=True)) as subtask_form:
                subtask_form.child_ids.add(grand_child_task_3)
            non_recurrent_subsubtask = non_recurrent_subsubtask.child_ids
            with Form(non_recurrent_subsubtask.with_context(tracking_disable=True)) as subtask_form:
                subtask_form.child_ids.add(grand_child_task_4)
            non_recurrent_subsubtask = non_recurrent_subsubtask.child_ids
            with Form(non_recurrent_subsubtask.with_context(tracking_disable=True)) as subtask_form:
                subtask_form.child_ids.add(grand_child_task_5)

            self.assertTrue(recurrent_subtask.recurrence_id)
            self.assertEqual(recurrent_subtask.recurrence_id.next_recurrence_date, date(2020, 1, 15))
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 8)
            self.assertEqual(project_subtask_count, 7)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 8, 'no extra task should be created')
            all_tasks = self.env['project.task'].search(domain)
            task_names = all_tasks.parent_id.mapped('name')
            self.assertEqual(task_names.count('Parent Task'), 1)
            self.assertEqual(task_names.count('Child task 2 that have recurrence'), 1)
            self.assertEqual(task_names.count('Grandchild task 2'), 1)
            self.assertEqual(task_names.count('Grandchild task 3'), 1)
            self.assertEqual(task_names.count('Grandchild task 4'), 1)

        # Phase 1 : Verify recurrences of Grandchild task 1 (recurrent)
        n = 8
        for i in range(1, 5):
            with freeze_time("2020-01-%02d" % (i + 1)):
                self.env['project.task.recurrence']._cron_create_recurring_tasks()
                project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
                self.assertEqual(project_task_count, n + i)  # + 1 occurence of task 3
                self.assertEqual(project_subtask_count, n + i - 1)
        with freeze_time("2020-01-11"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 12)  # total = 5 occurences of task 3
            self.assertEqual(project_subtask_count, 11)

        # Phase 2 : Verify recurrences of Child task 2 that have recurrence
        with freeze_time("2020-01-15"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            all_tasks = self.env['project.task'].search(domain)
            task_names = all_tasks.parent_id.mapped('name')
            self.assertEqual(task_names.count('Parent Task'), 1)
            self.assertEqual(task_names.count('Child task 2 that have recurrence'), 2)
            self.assertEqual(task_names.count('Grandchild task 2'), 2)
            self.assertEqual(task_names.count('Grandchild task 3'), 2)
            self.assertEqual(task_names.count('Grandchild task 4'), 1)
            self.assertEqual(len(task_names), 8)
            self.assertEqual(project_task_count, 12 + 1 + 4)  # 12 + the recurring task 5 + the 2 childs (3, 4) + 1 grandchild (5) + 1 grandgrandchild (6)
            self.assertEqual(project_subtask_count, 16)
            bottom_genealogy = all_tasks.filtered(lambda t: not t.child_ids.exists())
            bottom_genealogy_name = bottom_genealogy.mapped('name')
            self.assertEqual(bottom_genealogy_name.count('Child task 1'), 1)
            self.assertEqual(bottom_genealogy_name.count('Grandchild task 1 (recurrent)'), 6)
            # Grandchild task 5 should not be copied !
            self.assertEqual(bottom_genealogy_name.count('Grandchild task 5'), 1)

        # Phase 3 : Verify recurrences of the copy of Grandchild task 1 (recurrent)
        n = 17
        for i in range(1, 5):
            with freeze_time("2020-01-%02d" % (i + 15)):
                self.env['project.task.recurrence']._cron_create_recurring_tasks()
                project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
                self.assertEqual(project_task_count, n + i)
                self.assertEqual(project_subtask_count, n + i - 1)
        with freeze_time("2020-01-25"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 21)
            self.assertEqual(project_subtask_count, 20)

        # Phase 4 : No more recurrence
        with freeze_time("2020-02-15"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 21)
            self.assertEqual(project_subtask_count, 20)

        all_tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(all_tasks), 21)
        deadlines = all_tasks.sorted('create_date').mapped('date_deadline')
        self.assertTrue(bool(deadlines[-4]))
        self.assertTrue(bool(deadlines[-3]))
        del deadlines[-4]
        del deadlines[-3]
        self.assertTrue(not any(deadlines), "Deadline should not be copied")

        bottom_genealogy = all_tasks.filtered(lambda t: not t.child_ids.exists())
        bottom_genealogy_name = bottom_genealogy.mapped('name')
        self.assertEqual(bottom_genealogy_name.count('Child task 1'), 1)
        self.assertEqual(bottom_genealogy_name.count('Grandchild task 1 (recurrent)'), 10)
        self.assertEqual(bottom_genealogy_name.count('Grandchild task 5'), 1)

        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(all_tasks[0][f] == all_tasks[1][f] == all_tasks[2][f], "Field %s should have been copied" % f)

    def test_compute_recurrence_message_with_lang_not_set(self):
        task = self.env['project.task'].create({
            'name': 'Test task with user language not set',
            'project_id': self.project_recurring.id,
            'recurring_task': True,
            'repeat_interval': 1,
            'repeat_unit': 'week',
            'repeat_type': 'after',
            'repeat_number': 2,
            'mon': True,
        })

        self.env.user.lang = None
        task._compute_recurrence_message()

    def test_disabling_recurrence(self):
        """
        Disabling the recurrence of one task in a recurrence suite should disable *all*
        recurrences option on the tasks linked to that recurrence
        """
        with freeze_time("2020-01-01"):
            self.env['project.task'].create({
                'name': 'test recurring task',
                'project_id': self.project_recurring.id,
                'recurring_task': True,
                'repeat_interval': 1,
                'repeat_unit': 'week',
                'repeat_type': 'after',
                'repeat_number': 2,
                'mon': True,
            })

        with freeze_time("2020-01-06"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()

        with freeze_time("2020-01-13"):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()

        task_c, task_b, task_a = self.env['project.task'].search([('project_id', '=', self.project_recurring.id)])

        task_b.recurring_task = False

        self.assertFalse(any((task_a + task_b + task_c).mapped('recurring_task')),
                         "All tasks in the recurrence should have their recurrence disabled")
