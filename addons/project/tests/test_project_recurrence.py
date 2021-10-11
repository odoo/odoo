# -*- coding: utf-8 -*-


from odoo.tests.common import TransactionCase, Form

from datetime import date, datetime, timedelta
from dateutil import rrule
from freezegun import freeze_time
import logging

_logger = logging.getLogger(__name__)


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

    def set_task_create_date(self, task_id, create_date):
        self.env.cr.execute("UPDATE project_task SET create_date=%s WHERE id=%s", (create_date, task_id))

    # arj todo: move these test that generate dates in recurrence module ?
    def generate_date_range(self, rrule_args, duration=timedelta(hours=1), ):
        ranges = self.env['recurrence.recurrence']._range_calculation(record=None,
                                                                      duration=duration,
                                                                      batch_until=None,
                                                                      rrule_args=rrule_args)
        dates = [d[0] for d in ranges]
        dates.sort()
        return dates

    def test_recurrence_simple(self):
        with freeze_time("2020-02-15"):
            task = self.env['project.task'].create({
                'name': 'test recurring task',
                'description': 'my super recurring task bla bla bla',
                'project_id': self.project_recurring.id,
                'date_deadline': datetime(2020, 2, 1),
                'recurrency': True,
                'rrule_type': 'monthly',
                'interval': 1,
                'end_type': 'end_date',
                'until': date(2020, 3, 20),
                'month_by': 'date',
                'day': 15,
                'planned_hours': 2,
            })
            self.assertTrue(bool(task.recurrence_id), 'should create a recurrence')
            task.write(dict(interval=2, count=11, end_type='count', recurrence_update='all_records'))
            self.assertEqual(task.recurrence_id.interval, 2, 'recurrence should be updated')
            self.assertEqual(task.recurrence_id.count, 11, 'recurrence should be updated')
            tasks = task.recurrence_id._get_recurrent_records(model='project.task')
            self.assertEqual(len(tasks), 1)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(len(tasks), 1)
        with freeze_time("2020-02-1"):
            self.env['project.task'].create({
                'name': 'test recurring task',
                'description': 'my super recurring task bla bla bla',
                'project_id': self.project_recurring.id,
                'date_deadline': datetime(2020, 2, 1),
                'recurrency': True,
                'rrule_type': 'monthly',
                'interval': 1,
                'end_type': 'end_date',
                'until': date(2020, 3, 20),
                'month_by': 'date',
                'day': 15,
                'planned_hours': 2,
            })
            self.env['project.task']._cron_schedule_next()

    def test_recurrence_cron_repeat_after(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time("2020-01-01"):
            self.env['project.task'].create({
                'name': 'test recurring task',
                'description': 'my super recurring task bla bla bla',
                'project_id': self.project_recurring.id,
                'date_deadline': datetime(2020, 2, 1),
                'recurrency': True,
                'rrule_type': 'monthly',
                'interval': 1,
                'end_type': 'count',
                'count': 2,
                'month_by': 'date',
                'day': 1,
                'planned_hours': 2,
            })

            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time("2020-02-1"):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-03-1"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        tasks = self.env['project.task'].search(domain, order='start_datetime')
        self.assertEqual(len(tasks), 2)
        deadlines = tasks.mapped('date_deadline')
        self.assertEqual(deadlines[0], date(2020, 2, 1))
        self.assertFalse(tasks[1].date_deadline, "Deadline should not be copied")

    def test_recurrence_cron_repeat_until(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time("2020-01-15"):
            task = self.env['project.task'].create({
                'name': 'test recurring task',
                'description': 'my super recurring task bla bla bla',
                'project_id': self.project_recurring.id,
                'date_deadline':  datetime(2020, 2, 1),
                'recurrency': True,
                'rrule_type': 'monthly',
                'interval': 1,
                'end_type': 'end_date',
                'until': date(2020, 3, 20),
                'month_by': 'date',
                'day': 15,
                'planned_hours': 2,
            })
            self.assertTrue(task.recurrence_id, 'The task should have created a recurrence')
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time("2020-01-16"):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time("2020-02-15"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-03-15"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        with freeze_time("2020-04-15"):
            # Until is reached, no more task should be created
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(tasks), 3)

        self.assertTrue(bool(tasks[2].date_deadline))
        self.assertFalse(tasks[1].date_deadline, "Deadline should not be copied")

    def test_recurrence_cron_repeat_forever(self):
        domain = [('project_id', '=', self.project_recurring.id)]
        with freeze_time("2020-01-15"):
            self.env['project.task'].create({
                'name': 'test recurring task',
                'description': 'my super recurring task bla bla bla',
                'project_id': self.project_recurring.id,
                'date_deadline': datetime(2020, 2, 1),
                'recurrency': True,
                'rrule_type': 'monthly',
                'interval': 1,
                'end_type': 'forever',
                'month_by': 'date',
                'day': 15,
                'planned_hours': 2,
            })

            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 1, 'no extra task should be created')

        with freeze_time("2020-01-16"):
            self.assertEqual(self.env['project.task'].search_count(domain), 1)
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 1)

        with freeze_time("2020-02-15"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-02-16"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-02-17"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-02-17"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 2)

        with freeze_time("2020-03-15"):
            self.env['project.task']._cron_schedule_next()
            self.assertEqual(self.env['project.task'].search_count(domain), 3)

        tasks = self.env['project.task'].search(domain, order='start_datetime')
        self.assertEqual(len(tasks), 3)
        deadlines = tasks.mapped('date_deadline')
        self.assertEqual(deadlines[0], date(2020, 2, 1))
        self.assertFalse(tasks[1].date_deadline, "Deadline should not be copied")
        self.assertFalse(tasks[2].date_deadline, "Deadline should not be copied")

    def test_recurrence_update_task(self):

        with freeze_time("2020-01-01"):
            task = self.env['project.task'].create({
                    'name': 'test recurring task',
                    'start_datetime': datetime(2019, 12, 30),
                    'project_id': self.project_recurring.id,
                    'recurrency': True,
                    'interval': 1,
                    'rrule_type': 'weekly',
                    'wed': True,
                    'end_type': 'count',
                    'count': 3,
                    'mon': True,
                })
        with freeze_time("2020-01-06"):
            self.env['recurrence.recurrence']._cron_schedule_next('project.task')

        with freeze_time("2020-01-13"):
            self.env['recurrence.recurrence']._cron_schedule_next(model='project.task')
            self.assertEqual(task.recurrence_id.last_record_time, date(2020, 1, 6))

        task_c, task_b, task_a = self.env['project.task'].search([('project_id', '=', self.project_recurring.id)], order='start_datetime desc')
        (task_a+task_b+task_c).invalidate_cache()

        task_c.write({
            'name': 'my super updated task',
            'recurrence_update': 'all_records',
        })

        self.assertEqual(task_a.name, 'my super updated task')
        self.assertEqual(task_b.name, 'my super updated task')
        self.assertEqual(task_c.name, 'my super updated task')

        task_a.write({
            'name': 'don\'t you dare change my title',
            'recurrence_update': 'self_only',
        })

        self.assertEqual(task_a.name, 'don\'t you dare change my title')
        self.assertEqual(task_b.name, 'my super updated task')
        self.assertEqual(task_c.name, 'my super updated task')

        task_b.write({
            'description': 'hello!',
            'recurrence_update': 'future_records',
        })
        self.assertEqual(task_a.description, False)
        self.assertEqual(task_b.description, '<p>hello!</p>')
        self.assertEqual(task_c.description, '<p>hello!</p>')

    def test_recurrence_next_dates_week(self):
        rrule_args = dict(start_datetime=datetime(2020, 1, 1, 0, 0, 0),
                          interval=1,
                          rrule_type='weekly',
                          until=False,
                          month_by=False,
                          repeat_on_year=False,
                          weekdays=(rrule.MO.weekday),
                          weekday='MON',
                          count=5,
                          allday=False,
                          end_type='count',
                          day=1,
                          byday=1,
                          )
        dates = self.generate_date_range(rrule_args)
        self.assertEqual(dates[0], datetime(2020, 1, 6, 0, 0))
        self.assertEqual(dates[1], datetime(2020, 1, 13, 0, 0))
        self.assertEqual(dates[2], datetime(2020, 1, 20, 0, 0))
        self.assertEqual(dates[3], datetime(2020, 1, 27, 0, 0))
        self.assertEqual(dates[4], datetime(2020, 2, 3, 0, 0))

        rrule_args = dict(start_datetime=datetime(2020, 1, 1, 0, 0, 0),
                          interval=3,
                          rrule_type='weekly',
                          until=date(2020, 2, 1),
                          month_by=False,
                          repeat_on_year=False,
                          weekdays=(rrule.MO.weekday, rrule.FR.weekday),
                          weekday='MON',
                          count=100,
                          allday=False,
                          end_type='end_date',
                          day=1,
                          byday=1,
                          )
        dates = self.generate_date_range(rrule_args)
        self.assertEqual(len(dates), 3)
        self.assertEqual(dates[0], datetime(2020, 1, 3, 0, 0))
        self.assertEqual(dates[1], datetime(2020, 1, 20, 0, 0))
        self.assertEqual(dates[2], datetime(2020, 1, 24, 0, 0))

    def test_recurrence_next_dates_month(self):
        rrule_args = dict(start_datetime=datetime(2020, 1, 15, 0, 0, 0),
                          interval=1,
                          rrule_type='monthly',
                          until=False,
                          month_by='date',
                          repeat_on_year=False,
                          weekdays=False,
                          weekday=False,
                          count=12,
                          allday=False,
                          end_type='count',
                          day=31,
                          byday=-1,
                          )
        dates = self.generate_date_range(rrule_args)
        self.assertEqual(dates[0], datetime(2020, 1, 31))
        self.assertEqual(dates[1], datetime(2020, 3, 31))
        self.assertEqual(dates[2], datetime(2020, 5, 31))
        self.assertEqual(dates[3], datetime(2020, 7, 31))
        self.assertEqual(dates[4], datetime(2020, 8, 31))
        self.assertEqual(dates[5], datetime(2020, 10, 31))
        self.assertEqual(dates[6], datetime(2020, 12, 31))
        self.assertEqual(dates[7], datetime(2021, 1, 31))
        self.assertEqual(dates[8], datetime(2021, 3, 31))
        self.assertEqual(dates[9], datetime(2021, 5, 31))
        self.assertEqual(dates[10], datetime(2021, 7, 31))
        self.assertEqual(dates[11], datetime(2021, 8, 31))

        rrule_args = dict(start_datetime=datetime(2020, 2, 20, 0, 0, 0),
                          interval=3,
                          rrule_type='monthly',
                          until=False,
                          month_by='date',
                          repeat_on_year=False,
                          weekdays=False,
                          weekday=False,
                          count=5,
                          allday=False,
                          end_type='count',
                          day=29,
                          byday=False,
                          )
        dates = self.generate_date_range(rrule_args)
        self.assertEqual(dates[0], datetime(2020, 2, 29))
        self.assertEqual(dates[1], datetime(2020, 5, 29))
        self.assertEqual(dates[2], datetime(2020, 8, 29))
        self.assertEqual(dates[3], datetime(2020, 11, 29))
        self.assertEqual(dates[4], datetime(2021, 5, 29))

        rrule_args = dict(start_datetime=datetime(2020, 1, 10, 0, 0, 0),
                          interval=1,
                          rrule_type='monthly',
                          until=datetime(2020, 5, 31),
                          weekday='SAT',
                          byweekday=[rrule.SA(4), ],
                          count=False,
                          allday=False,
                          end_type='end_date',
                          day=False,
                          byday='4',
                          month_by='day',
                          )
        dates = self.generate_date_range(rrule_args)
        self.assertEqual(len(dates), 5)
        self.assertEqual(dates[0], datetime(2020, 1, 25))
        self.assertEqual(dates[1], datetime(2020, 2, 22))
        self.assertEqual(dates[2], datetime(2020, 3, 28))
        self.assertEqual(dates[3], datetime(2020, 4, 25))
        self.assertEqual(dates[4], datetime(2020, 5, 23))

    def test_recurrence_next_dates_year(self):
        rrule_args = {'interval': 1, 'start_datetime': datetime(2020, 11, 30), 'rrule_type': 'yearly',
                      'end_type': 'end_date', 'until': date(2026, 1, 1), 'day': 30, 'month_by': 'date'}
        dates = self.generate_date_range(rrule_args)
        self.assertEqual(len(dates), 6)
        self.assertEqual(dates[0], datetime(2020, 11, 30))
        self.assertEqual(dates[1], datetime(2021, 11, 30))
        self.assertEqual(dates[2], datetime(2022, 11, 30))
        self.assertEqual(dates[3], datetime(2023, 11, 30))
        self.assertEqual(dates[4], datetime(2024, 11, 30))
        self.assertEqual(dates[5], datetime(2025, 11, 30))

    def test_recurrence_cron_repeat_after_subtasks(self):
        """
        Create a parent task which have a subtask. This subtask is recurrent
        :return:
        """
        def get_task_and_subtask_counts(domain):
            tasks = self.env['project.task'].search(domain)
            return len(tasks), len(tasks.filtered('parent_id'))

        parent_task = self.env['project.task'].create({
            'name': 'Parent Task',
            'project_id': self.project_recurring.id
        })
        domain = [('project_id', '=', self.project_recurring.id)]
        with Form(parent_task.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.new() as subtask_form:
                subtask_form.name = 'Test Subtask 1'
        with freeze_time("2020-01-01"):
            subtask = parent_task.child_ids
            subtask.start_datetime = '2020-01-01'
            subtask.stop_datetime = subtask.start_datetime + timedelta(hours=1)
            subtask.write({'recurrency': True, 'interval': 1, 'rrule_type': 'monthly', 'end_type': 'count',
                           'count': 3, 'month_by': 'date', 'day': 15, 'date_deadline':  datetime(2020, 2, 1)})
            subtask.planned_hours = 2
            self.assertTrue(subtask.recurrence_id)
            # First task (base record) is moved to 2020-01-15
            self.assertEqual(subtask.start_datetime, datetime(2020, 1, 15))
            self.assertFalse(subtask.recurrence_id.last_record_time)
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 2)
            self.assertEqual(project_subtask_count, 1)
            self.assertEqual(self.env['project.task'].search_count(domain), 2, 'no extra task should be created')

        with freeze_time("2020-01-16"):
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 2)
            self.assertEqual(project_subtask_count, 1)
            self.env['recurrence.recurrence']._cron_schedule_next(model='project.task')
            # parent task is not affected. The child task is recurrent, it should create another one
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 2)
            self.assertEqual(project_subtask_count, 1)

        with freeze_time("2020-02-16"):
            self.env['recurrence.recurrence']._cron_schedule_next(model='project.task')
            # parent task is not affected. The child task is recurrent, it should create another one
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 3)
            self.assertEqual(project_subtask_count, 2)
            self.env['recurrence.recurrence']._cron_schedule_next(model='project.task')
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 3)
            self.assertEqual(project_subtask_count, 2)

        tasks = self.env['project.task'].search(domain)
        deadlines = tasks.mapped('child_ids').mapped('date_deadline')
        self.assertEqual(len(deadlines), 2)
        self.assertTrue(bool(deadlines[0]))
        self.assertFalse(deadlines[1], "Deadline should not be copied")

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
        parent_task = self.env['project.task'].create({
            'name': 'Parent Task',
            'project_id': self.project_recurring.id
        })
        domain = [('project_id', '=', self.project_recurring.id)]
        duration = timedelta(hours=1)
        with Form(parent_task.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.new() as subtask_form:
                subtask_form.name = 'Child task 1'
        with Form(parent_task.with_context({'tracking_disable': True})) as task_form:
            with task_form.child_ids.new() as subtask_form:
                subtask_form.name = 'Child task 2 that have recurrence'
        with freeze_time("2020-01-01"):
            recurrent_subtask = parent_task.child_ids[0]
            recurrent_subtask.write({'start_datetime': datetime(2020, 1, 1),
                                     'stop_datetime': datetime(2020, 1, 1) + duration,
                                     'recurrency': True, 'interval': 1,
                                     'rrule_type': 'monthly', 'end_type': 'count',
                                     'count': 3, 'month_by': 'date', 'day': 15, 'date_deadline': datetime(2020, 2, 1),
                                     })
            with Form(recurrent_subtask.with_context(tracking_disable=True)) as task_form:
                with task_form.child_ids.new() as subtask_form:
                    subtask_form.name = 'Grandchild task 1 (recurrent)'
                with task_form.child_ids.new() as subtask_form:
                    subtask_form.name = 'Grandchild task 2'

            # configure recurring subtask
            recurrent_subsubtask = recurrent_subtask.child_ids.filtered(lambda t: t.name == 'Grandchild task 1 (recurrent)')
            non_recurrent_subsubtask = recurrent_subtask.child_ids.filtered(lambda t: t.name == 'Grandchild task 2')
            recurrent_subsubtask.write({'start_datetime': datetime(2020, 1, 1),
                                        'stop_datetime': datetime(2020, 1, 1) + duration,
                                        'recurrency': True, 'interval': 1, 'rrule_type': 'daily', 'end_type': 'count',
                                        'count': 5, 'date_deadline': datetime(2020, 2, 3),
                                        })

            # create non-recurring grandchild subtasks
            with Form(non_recurrent_subsubtask.with_context(tracking_disable=True)) as subtask_form:
                with subtask_form.child_ids.new() as subsubtask_form:
                    subsubtask_form.name = 'Grandchild task 3'
            # Inception, we reuse the variable name but we go deeper in the child generation
            non_recurrent_subsubtask = non_recurrent_subsubtask.child_ids
            with Form(non_recurrent_subsubtask.with_context(tracking_disable=True)) as subtask_form:
                with subtask_form.child_ids.new() as subsubtask_form:
                    subsubtask_form.name = 'Grandchild task 4'
            # Inception, we reuse the variable name but we go deeper in the child generation
            non_recurrent_subsubtask = non_recurrent_subsubtask.child_ids
            with Form(non_recurrent_subsubtask.with_context(tracking_disable=True)) as subtask_form:
                with subtask_form.child_ids.new() as subsubtask_form:
                    subsubtask_form.name = 'Grandchild task 5'

            self.assertTrue(recurrent_subtask.recurrence_id)
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 8)
            self.assertEqual(project_subtask_count, 7)
            self.env['project.task']._cron_schedule_next()
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
                self.env['project.task']._cron_schedule_next()
                project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
                self.assertEqual(project_task_count, n + i)  # + 1 occurence of task 3
                self.assertEqual(project_subtask_count, n + i - 1)
        with freeze_time("2020-01-11"):
            self.env['project.task']._cron_schedule_next()
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 12)  # total = 5 occurences of task 3
            self.assertEqual(project_subtask_count, 11)

        # Phase 2 : Verify recurrences of Child task 2 that have recurrence
        with freeze_time("2020-02-15"):
            self.env['project.task']._cron_schedule_next()
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            all_tasks = self.env['project.task'].search(domain)
            task_names = all_tasks.parent_id.mapped('name')
            self.assertEqual(task_names.count('Parent Task'), 1)
            self.assertEqual(task_names.count('Child task 2 that have recurrence'), 2)
            self.assertEqual(task_names.count('Grandchild task 2'), 2)
            self.assertEqual(task_names.count('Grandchild task 3'), 2)
            self.assertEqual(task_names.count('Grandchild task 4'), 1)
            self.assertEqual(len(task_names), 8)
            self.assertEqual(project_task_count, 12 + 1 + 3 + 2)  # 12 + one 'child task 2 (recurrent)' + Grandchildtask (2,3,4) + two grand child task 1 (recurrent)
            self.assertEqual(project_subtask_count, 17)
            bottom_genealogy = all_tasks.filtered(lambda t: not t.child_ids.exists())
            bottom_genealogy_name = bottom_genealogy.mapped('name')
            self.assertEqual(bottom_genealogy_name.count('Child task 1'), 1)
            self.assertEqual(bottom_genealogy_name.count('Grandchild task 1 (recurrent)'), 7)
            # Grandchild task 5 should not be copied !
            self.assertEqual(bottom_genealogy_name.count('Grandchild task 5'), 1)

        # Phase 3 : Verify recurrences of the copy of Grandchild task 1 (recurrent)
        with freeze_time("2020-03-15"):
            self.env['project.task']._cron_schedule_next()
            project_task_count, project_subtask_count = get_task_and_subtask_counts(domain)
            self.assertEqual(project_task_count, 28)
            self.assertEqual(project_subtask_count, 27)
            # Phase 4 : No more recurrence
            self.env['project.task'].with_context(arj=True)._cron_schedule_next()

        all_tasks = self.env['project.task'].search(domain)
        self.assertEqual(len(all_tasks), 28)
        deadlines = all_tasks.sorted('create_date').mapped('date_deadline')
        self.assertTrue(bool(deadlines[-4]))
        self.assertTrue(bool(deadlines[-3]))
        del deadlines[-4]
        del deadlines[-3]
        self.assertTrue(not any(deadlines), "Deadline should not be copied")

        bottom_genealogy = all_tasks.filtered(lambda t: not t.child_ids.exists())
        bottom_genealogy_name = bottom_genealogy.mapped('name')
        self.assertEqual(bottom_genealogy_name.count('Child task 1'), 1)
        self.assertEqual(bottom_genealogy_name.count('Grandchild task 1 (recurrent)'), 13)
        self.assertEqual(bottom_genealogy_name.count('Grandchild task 5'), 1)

        for f in self.env['project.task']._get_recurring_fields():
            self.assertTrue(all_tasks[0][f] == all_tasks[1][f] == all_tasks[2][f], "Field %s should have been copied" % f)
