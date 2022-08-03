# -*- coding: utf-8 -*-

from odoo import fields, Command
from odoo.tests.common import Form, TransactionCase
from odoo.exceptions import ValidationError

from datetime import date, datetime, time
from dateutil.rrule import MO, TU, WE, TH, FR, SA, SU
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time


class TestProjectRecurrence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestProjectRecurrence, cls).setUpClass()

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

        cls.classPatch(cls.env.cr, 'now', fields.Datetime.now)

        cls.date_01_01 = datetime.combine(datetime.now() + relativedelta(years=-1, month=1, day=1), time(0, 0))
        cls.date_01_15 = cls.date_01_01 + relativedelta(day=15)
        cls.date_02_01 = cls.date_01_01 + relativedelta(month=2)
        cls.date_02_15 = cls.date_01_01 + relativedelta(month=2, day=15)

    def test_recurrence_simple(self):
        with freeze_time(self.date_01_01):
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
            self.assertEqual(task.recurrence_id.next_recurrence_date, (self.date_01_01 + relativedelta(day=31)).date())

            task.recurring_task = False
            self.assertFalse(bool(task.recurrence_id), 'the recurrence should be deleted')

    def test_recurrence_cron_repeat_after(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time(self.date_01_01):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.description = 'my super recurring task bla bla bla'
            form.project_id = self.project_recurring
            form.date_deadline = self.date_02_01

            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = 'month'
            form.repeat_type = 'after'
            form.repeat_number = 2
            form.repeat_on_month = 'date'
            form.repeat_day = '15'
            task = form.save()
            task.write({
                'planned_hours': 2.0,
                'recurrence_update': 'subsequent',
            })
            self.assertEqual(task.recurrence_id.next_recurrence_date, self.date_01_15.date())
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')
            self.assertEqual(task.recurrence_id.recurrence_left, 2)

        with freeze_time(self.date_01_15):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)
            self.assertEqual(task.recurrence_id.recurrence_left, 1)

        with freeze_time(self.date_02_15):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)
            self.assertEqual(task.recurrence_id.recurrence_left, 0)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)
            self.assertEqual(task.recurrence_id.recurrence_left, 0)


        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 3)
        self.assertTrue(
               tasks[0].date_deadline - tasks[0].create_date.date()\
            == tasks[1].date_deadline - tasks[1].create_date.date()\
            == tasks[2].date_deadline - tasks[2].create_date.date(),
            'all tasks sould have the same period between their create_date and date_deadline'
        )

        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(tasks[0][f] == tasks[1][f] == tasks[2][f], "Field %s should have been copied" % f)

    def test_recurrence_cron_repeat_until(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time(self.date_01_01):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.description = 'my super recurring task bla bla bla'
            form.project_id = self.project_recurring
            form.date_deadline = self.date_02_01

            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = 'month'
            form.repeat_type = 'until'
            form.repeat_until = self.date_02_01 + relativedelta(days=20)
            form.repeat_on_month = 'date'
            form.repeat_day = '15'
            task = form.save()
            task.write({
                'planned_hours': 2.0,
                'recurrence_update': 'subsequent',
            })
            self.assertEqual(task.recurrence_id.next_recurrence_date, self.date_01_15.date())
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time(self.date_01_15):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time(self.date_02_15):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 3)
        self.assertTrue(
               tasks[0].date_deadline - tasks[0].create_date.date()\
            == tasks[1].date_deadline - tasks[1].create_date.date()\
            == tasks[2].date_deadline - tasks[2].create_date.date(),
            'all tasks sould have the same period between their create_date and date_deadline'
        )

        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(tasks[0][f] == tasks[1][f] == tasks[2][f], "Field %s should have been copied" % f)

    def test_recurrence_cron_repeat_forever(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time(self.date_01_01):
            form = Form(self.env['project.task'])
            form.name = 'test recurring task'
            form.description = 'my super recurring task bla bla bla'
            form.project_id = self.project_recurring
            form.date_deadline = self.date_02_01

            form.recurring_task = True
            form.repeat_interval = 1
            form.repeat_unit = 'month'
            form.repeat_type = 'forever'
            form.repeat_on_month = 'date'
            form.repeat_day = '15'
            task = form.save()
            task.write({
                'planned_hours': 2.0,
                'recurrence_update': 'subsequent',
            })

            self.assertEqual(task.recurrence_id.next_recurrence_date, self.date_01_15.date())
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time(self.date_01_15):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time(self.date_02_15):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time(self.date_02_15):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time(self.date_02_15 + relativedelta(days=1)):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time(self.date_02_15 + relativedelta(days=2)):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time(self.date_02_15 + relativedelta(months=1)):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            self.assertEqual(self.env['project.task'].search_count(domain), 4)

        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 4)
        self.assertTrue(
               tasks[0].date_deadline - tasks[0].create_date.date()\
            == tasks[1].date_deadline - tasks[1].create_date.date()\
            == tasks[2].date_deadline - tasks[2].create_date.date()\
            == tasks[3].date_deadline - tasks[3].create_date.date(),
            'all tasks sould have the same period between their create_date and date_deadline'
        )
        for f in self.env['project.task.recurrence']._get_recurring_fields():
            self.assertTrue(
                tasks[0][f] == tasks[1][f] == tasks[2][f] == tasks[3][f],
                "Field %s should have been copied" % f)

    def test_recurrence_update_task(self):
        with freeze_time(self.date_01_01):
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

        with freeze_time(self.date_01_01 + relativedelta(day=6)):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            task.write({
                'name': 'my super updated task',
                'recurrence_update': 'subsequent',
            })
            task.write({
                'description': '<p>hello!</p>',
                'recurrence_update': 'this',
            })

        with freeze_time(self.date_01_01 + relativedelta(day=13)):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()

        task_c, task_b, task_a = self.env['project.task'].search([('project_id', '=', self.project_recurring.id)])

        self.assertEqual(task_a.name, 'my super updated task', 'This task has been directly updated')
        self.assertEqual(task_b.name, 'test recurring task', 'As this task already existed, it should not have been updated')
        self.assertEqual(task_c.name, 'my super updated task', 'As this task was created after template modification, it should be updated')

        self.assertEqual(task_a.description, '<p>hello!</p>', 'This task has been directly updated')
        self.assertEqual(task_b.description, False, 'Subsequent tasks should not be affected by "this" modifications')
        self.assertEqual(task_c.description, False, 'Subsequent tasks should not be affected by "this" modifications')

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

    def test_change_subtask_of_recurrent_task(self):
        with freeze_time(self.date_01_01):
            task = self.env['project.task'].create({
                'name': 'recurring task',
                'project_id': self.project_recurring.id,
                'recurring_task': True,
                'repeat_interval': 2,
                'repeat_unit': 'week',
                'repeat_type': 'after',
                'repeat_number': 2,
                'mon': True,
                'child_ids': [Command.create({
                    'name': 'subtask',
                })],
            })
            recurrence = task.recurrence_id
            task.child_ids.write({
                'name': 'subtask 1',
                'recurrence_update': 'subsequent',
            })

        with freeze_time(self.date_01_15):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            child = recurrence.task_ids.sorted('create_date', reverse=True)[0].child_ids
            self.assertEqual(child.name, 'subtask 1')
            child.write({
                'name': 'subtask 2',
                'recurrence_update': 'this',
            })

        with freeze_time(self.date_02_01):
            self.env['project.task.recurrence']._cron_create_recurring_tasks()
            child = recurrence.task_ids.sorted('create_date', reverse=True)[0].child_ids
            self.assertEqual(child.name, 'subtask 1')

        with self.assertRaises(ValidationError):
            child.write({
                'recurring_task': True,
                'repeat_unit': 'week',
            })
