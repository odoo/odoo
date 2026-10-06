from ast import literal_eval
from datetime import timedelta

from odoo.exceptions import AccessError
from odoo.fields import Command
from odoo.tests import tagged

from .test_project_base import TestProjectCommon


@tagged('post_install', '-at_install')
class TestProjectTimeByStageReport(TestProjectCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.now = cls.env.cr.now().replace(microsecond=0)
        cls.stage_new, cls.stage_doing, cls.stage_done = cls.env['project.task.type'].create([
            {'name': 'New', 'sequence': 1},
            {'name': 'Doing', 'sequence': 10},
            {'name': 'Done', 'sequence': 20},
        ])
        cls.project_cows = cls.env['project.project'].create({
            'name': 'Cows',
            'type_ids': [Command.set((cls.stage_new + cls.stage_doing + cls.stage_done).ids)],
        })

    def _create_task(self, stage, days_ago, **vals):
        """ Create a task in ``stage``, as if it was created ``days_ago`` days ago. """
        with self.mock_datetime_and_now(self.now - timedelta(days=days_ago)):
            task = self.env['project.task'].create({
                'name': 'Cows Task',
                'project_id': self.project_cows.id,
                'stage_id': stage.id,
                **vals,
            })
            self.env.flush_all()
        return task

    def _move_task(self, task, stage, days_ago):
        """ Move ``task`` to ``stage``, as if it was moved ``days_ago`` days ago. """
        with self.mock_datetime_and_now(self.now - timedelta(days=days_ago)):
            task.stage_id = stage
            self.env.flush_all()

    def _get_hours_per_stage(self, task):
        report_lines = self.env['project.task.stage.report'].search([('task_id', '=', task.id)])
        return {line.stage_id: line.time_spent for line in report_lines}

    def test_time_spent_per_stage(self):
        task = self._create_task(self.stage_new, days_ago=5)
        self._move_task(task, self.stage_doing, days_ago=2)

        self.assertEqual(
            self._get_hours_per_stage(task),
            {self.stage_new: 72.0, self.stage_doing: 48.0},
            "The current stage should count the time spent in it up to now.",
        )

    def test_time_spent_on_revisited_stage(self):
        task = self._create_task(self.stage_new, days_ago=6)
        self._move_task(task, self.stage_doing, days_ago=5)
        self._move_task(task, self.stage_new, days_ago=4)
        self._move_task(task, self.stage_doing, days_ago=1)

        self.assertEqual(
            self._get_hours_per_stage(task),
            {self.stage_new: 96.0, self.stage_doing: 48.0},
            "Every visit of a stage should be summed, including the ongoing one.",
        )

    def test_average_time_spent_by_stage(self):
        first_task = self._create_task(self.stage_new, days_ago=4)
        self._move_task(first_task, self.stage_doing, days_ago=1)
        second_task = self._create_task(self.stage_new, days_ago=2)
        self._move_task(second_task, self.stage_doing, days_ago=1)

        groups = self.env['project.task.stage.report']._read_group(
            [('project_id', '=', self.project_cows.id)],
            ['stage_id'],
            ['time_spent:avg', '__count'],
        )
        self.assertEqual(
            groups,
            [(self.stage_new, 48.0, 2), (self.stage_doing, 24.0, 2)],
            "Grouped by stage, the report should show the average time the tasks spent in it.",
        )

    def test_report_is_closed(self):
        open_task = self._create_task(self.stage_new, days_ago=1)
        done_task = self._create_task(self.stage_new, days_ago=1, state='1_done')
        canceled_task = self._create_task(self.stage_new, days_ago=1, state='1_canceled')
        Report = self.env['project.task.stage.report']
        project_domain = [('project_id', '=', self.project_cows.id)]

        self.assertEqual(
            Report.search(project_domain + [('is_closed', '=', True)]).task_id,
            done_task + canceled_task,
            "Done and canceled tasks should be reported as closed.",
        )
        self.assertEqual(
            Report.search(project_domain + [('is_closed', '=', False)]).task_id,
            open_task,
            "Tasks that are neither done nor canceled should be reported as open.",
        )

    def test_report_excludes_private_tasks(self):
        private_task = self.env['project.task'].create({
            'name': 'Private Task',
            'user_ids': [Command.set(self.env.user.ids)],
        })
        self.env.flush_all()

        self.assertFalse(
            self.env['project.task.stage.report'].search([('task_id', '=', private_task.id)]),
            "Private tasks should not be in the report.",
        )

    def test_report_access_rights(self):
        task = self._create_task(self.stage_new, days_ago=1)
        Report = self.env['project.task.stage.report']

        manager_lines = Report.with_user(self.user_projectmanager).search([('task_id', '=', task.id)])
        self.assertEqual(manager_lines.time_spent, 24.0, "A project manager should be able to read the report.")

        with self.assertRaises(AccessError, msg="A project user should not be able to read the report."):
            Report.with_user(self.user_projectuser).search([('task_id', '=', task.id)])

    def test_action_project_time_by_stage_report(self):
        cows_task = self._create_task(self.stage_new, days_ago=1)
        self._move_task(self.task_1, self.stage_new, days_ago=1)
        Report = self.env['project.task.stage.report']
        self.assertTrue(
            Report.search([('task_id', '=', self.task_1.id)]),
            "The task of the other project should be in the report, for the domain check below to be meaningful.",
        )

        action = self.project_cows.with_user(self.user_projectmanager).action_project_time_by_stage_report()
        self.assertEqual(
            action['res_model'], 'project.task.stage.report',
            "The action should open the time by stage report.",
        )
        self.assertEqual(
            action['display_name'], "Cows's Time by Stage",
            "The action should be named after the project.",
        )

        domain = literal_eval(action['domain'].replace('active_id', str(self.project_cows.id)))
        self.assertEqual(Report.search(domain).task_id, cows_task, "Only the tasks of the project should be reported.")
