# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from datetime import datetime

from odoo import Command
from odoo.osv.expression import AND, OR
from odoo.tests.common import tagged, HttpCase
from .test_project_base import TestProjectCommon


class TestBurndownChartCommon(TestProjectCommon):

    @classmethod
    def set_create_date(cls, table, res_id, create_date):
        cls.env.cr.execute("UPDATE {} SET create_date=%s WHERE id=%s".format(table), (create_date, res_id))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.current_year = datetime.now().year
        create_date = datetime(cls.current_year - 1, 1, 1)
        kanban_state_vals = {
            "legend_blocked": 'Blocked',
            "legend_done": 'Ready',
            "legend_normal": 'In Progress'
        }
        Stage = cls.env['project.task.type']
        cls.todo_stage = Stage.create({
            'sequence': 1,
            'name': 'TODO',
            **kanban_state_vals,
        })
        cls.set_create_date('project_task_type', cls.todo_stage.id, create_date)
        cls.in_progress_stage = Stage.create({
            'sequence': 10,
            'name': 'In Progress',
            **kanban_state_vals,
        })
        cls.set_create_date('project_task_type', cls.in_progress_stage.id, create_date)
        cls.testing_stage = Stage.create({
            'sequence': 20,
            'name': 'Testing',
            **kanban_state_vals,
        })
        cls.set_create_date('project_task_type', cls.testing_stage.id, create_date)
        cls.done_stage = Stage.create({
            'sequence': 30,
            'name': 'Done',
            **kanban_state_vals,
        })
        cls.set_create_date('project_task_type', cls.done_stage.id, create_date)
        cls.stages = cls.todo_stage + cls.in_progress_stage + cls.testing_stage + cls.done_stage
        cls.project = cls.env['project.project'].create({
            'name': 'Burndown Chart Test',
            'privacy_visibility': 'employees',
            'alias_name': 'project+burndown_chart',
            'type_ids': [Command.link(stage_id) for stage_id in cls.stages.ids],
        })
        cls.set_create_date('project_project', cls.project.id, create_date)
        cls.project.invalidate_model()
        cls.milestone = cls.env['project.milestone'].with_context({'mail_create_nolog': True}).create({
            'name': 'Test Milestone',
            'project_id': cls.project_pigs.id,
        })
        cls.task_a = cls.env['project.task'].create({
            'name': 'Task A',
            'priority': 0,
            'project_id': cls.project.id,
            'stage_id': cls.todo_stage.id,
        })
        cls.set_create_date('project_task', cls.task_a.id, create_date)
        cls.task_b = cls.task_a.copy({
            'name': 'Task B',
            'user_ids': [Command.set([cls.user_projectuser.id, cls.user_projectmanager.id])],
        })
        cls.set_create_date('project_task', cls.task_b.id, create_date)
        cls.task_c = cls.task_a.copy({
            'name': 'Task C',
            'partner_id': cls.partner_1.id,
            'user_ids': [Command.link(cls.user_projectuser.id)],
        })
        cls.set_create_date('project_task', cls.task_c.id, create_date)
        cls.task_d = cls.task_a.copy({
            'name': 'Task D',
            'milestone_id': cls.milestone.id,
            'user_ids': [Command.link(cls.user_projectmanager.id)],
        })
        cls.set_create_date('project_task', cls.task_d.id, create_date)
        cls.task_e = cls.task_a.copy({
            'name': 'Task E',
            'partner_id': cls.partner_1.id,
        })
        cls.set_create_date('project_task', cls.task_e.id, create_date)

        # Create a new task to check if a task without changing its stage is taken into account
        task_f = cls.env['project.task'].create({
            'name': 'Task F',
            'priority': 0,
            'project_id': cls.project.id,
            'milestone_id': cls.milestone.id,
            'stage_id': cls.todo_stage.id,
        })
        cls.set_create_date('project_task', task_f.id, datetime(cls.current_year - 1, 12, 20))

        cls.project_2 = cls.env['project.project'].create({
            'name': 'Burndown Chart Test 2 mySearchTag',
            'privacy_visibility': 'employees',
            'alias_name': 'project+burndown_chart+2',
            'type_ids': [Command.link(stage_id) for stage_id in cls.stages.ids],
        })
        cls.set_create_date('project_project', cls.project_2.id, create_date)
        cls.project.invalidate_model()
        cls.task_g = cls.env['project.task'].create({
            'name': 'Task G',
            'priority': 0,
            'project_id': cls.project_2.id,
            'stage_id': cls.todo_stage.id,
            'user_ids': [Command.link(cls.user_projectuser.id)],
        })
        cls.set_create_date('project_task', cls.task_g.id, create_date)
        cls.task_h = cls.task_g.copy({
            'name': 'Task H',
            'user_ids': [Command.link(cls.user_projectmanager.id)],
        })
        cls.set_create_date('project_task', cls.task_h.id, create_date)

        # Precommit to have the records in db and allow to rollback at the end of test
        cls.env.cr.flush()

        with freeze_time('%s-02-10' % (cls.current_year - 1)):
            (cls.task_a + cls.task_b).write({'stage_id': cls.in_progress_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-02-20' % (cls.current_year - 1)):
            cls.task_c.write({'stage_id': cls.in_progress_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-03-15' % (cls.current_year - 1)):
            (cls.task_d + cls.task_e).write({'stage_id': cls.in_progress_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-04-10' % (cls.current_year - 1)):
            (cls.task_a + cls.task_b).write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-05-12' % (cls.current_year - 1)):
            cls.task_c.write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-06-25' % (cls.current_year - 1)):
            cls.task_d.write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-07-25' % (cls.current_year - 1)):
            cls.task_e.write({'stage_id': cls.testing_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-08-01' % (cls.current_year - 1)):
            cls.task_a.write({'stage_id': cls.done_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-09-10' % (cls.current_year - 1)):
            cls.task_b.write({'stage_id': cls.done_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-10-05' % (cls.current_year - 1)):
            cls.task_c.write({'stage_id': cls.done_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-11-25' % (cls.current_year - 1)):
            cls.task_d.write({'stage_id': cls.done_stage.id})
            cls.env.cr.flush()

        with freeze_time('%s-12-12' % (cls.current_year - 1)):
            cls.task_e.write({'stage_id': cls.done_stage.id})
            cls.env.cr.flush()


class TestBurndownChart(TestBurndownChartCommon):

    def map_read_group_result(self, read_group_result):
        return {(res['date:month'], res['stage_id'][0]): res['__count'] for res in read_group_result if res['stage_id'][1]}

    def check_read_group_results(self, domain, expected_results_dict):
        stages_dict = {stage.id: stage.name for stage in self.stages}
        read_group_result = self.env['project.task.burndown.chart.report'].read_group(
            domain, ['date', 'stage_id'], ['date:month', 'stage_id'], lazy=False)
        read_group_result_dict = self.map_read_group_result(read_group_result)
        for (month, stage_id), __count in read_group_result_dict.items():
            expected_count = expected_results_dict.get((month, stage_id), 100000)
            self.assertEqual(
                __count,
                expected_count,
                'In %s, the number of tasks should be equal to %s in %s stage.' % (month, expected_count, stages_dict.get(stage_id, 'Unknown'))
            )

    def test_burndown_chart(self):
        burndown_chart_domain = [('display_project_id', '!=', False)]
        project_domain = [('project_id', '=', self.project.id)]

        # Check that we get the expected results for the complete data of `self.project`.
        project_expected_dict = {
            ('January %s' % (self.current_year - 1), self.todo_stage.id): 5,
            ('January %s' % (self.current_year - 1), self.in_progress_stage.id): 0,
            ('January %s' % (self.current_year - 1), self.testing_stage.id): 0,
            ('January %s' % (self.current_year - 1), self.done_stage.id): 0,
            ('February %s' % (self.current_year - 1), self.todo_stage.id): 2,
            ('February %s' % (self.current_year - 1), self.in_progress_stage.id): 3,
            ('February %s' % (self.current_year - 1), self.testing_stage.id): 0,
            ('February %s' % (self.current_year - 1), self.done_stage.id): 0,
            ('March %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('March %s' % (self.current_year - 1), self.in_progress_stage.id): 5,
            ('March %s' % (self.current_year - 1), self.testing_stage.id): 0,
            ('March %s' % (self.current_year - 1), self.done_stage.id): 0,
            ('April %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('April %s' % (self.current_year - 1), self.in_progress_stage.id): 3,
            ('April %s' % (self.current_year - 1), self.testing_stage.id): 2,
            ('April %s' % (self.current_year - 1), self.done_stage.id): 0,
            ('May %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('May %s' % (self.current_year - 1), self.in_progress_stage.id): 2,
            ('May %s' % (self.current_year - 1), self.testing_stage.id): 3,
            ('May %s' % (self.current_year - 1), self.done_stage.id): 0,
            ('June %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('June %s' % (self.current_year - 1), self.in_progress_stage.id): 1,
            ('June %s' % (self.current_year - 1), self.testing_stage.id): 4,
            ('June %s' % (self.current_year - 1), self.done_stage.id): 0,
            ('July %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('July %s' % (self.current_year - 1), self.in_progress_stage.id): 0,
            ('July %s' % (self.current_year - 1), self.testing_stage.id): 5,
            ('July %s' % (self.current_year - 1), self.done_stage.id): 0,
            ('August %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('August %s' % (self.current_year - 1), self.in_progress_stage.id): 0,
            ('August %s' % (self.current_year - 1), self.testing_stage.id): 4,
            ('August %s' % (self.current_year - 1), self.done_stage.id): 1,
            ('September %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('September %s' % (self.current_year - 1), self.in_progress_stage.id): 0,
            ('September %s' % (self.current_year - 1), self.testing_stage.id): 3,
            ('September %s' % (self.current_year - 1), self.done_stage.id): 2,
            ('October %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('October %s' % (self.current_year - 1), self.in_progress_stage.id): 0,
            ('October %s' % (self.current_year - 1), self.testing_stage.id): 2,
            ('October %s' % (self.current_year - 1), self.done_stage.id): 3,
            ('November %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('November %s' % (self.current_year - 1), self.in_progress_stage.id): 0,
            ('November %s' % (self.current_year - 1), self.testing_stage.id): 1,
            ('November %s' % (self.current_year - 1), self.done_stage.id): 4,
            ('December %s' % (self.current_year - 1), self.todo_stage.id): 0,
            ('December %s' % (self.current_year - 1), self.in_progress_stage.id): 0,
            ('December %s' % (self.current_year - 1), self.done_stage.id): 5,
            ('December %s' % (self.current_year - 1), self.todo_stage.id): 1,
            ('January %s' % (self.current_year), self.todo_stage.id): 0,
            ('January %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('January %s' % (self.current_year), self.done_stage.id): 5,
            ('January %s' % (self.current_year), self.todo_stage.id): 1,
            ('February %s' % (self.current_year), self.todo_stage.id): 0,
            ('February %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('February %s' % (self.current_year), self.done_stage.id): 5,
            ('February %s' % (self.current_year), self.todo_stage.id): 1,
            ('March %s' % (self.current_year), self.todo_stage.id): 0,
            ('March %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('March %s' % (self.current_year), self.done_stage.id): 5,
            ('March %s' % (self.current_year), self.todo_stage.id): 1,
            ('April %s' % (self.current_year), self.todo_stage.id): 0,
            ('April %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('April %s' % (self.current_year), self.done_stage.id): 5,
            ('April %s' % (self.current_year), self.todo_stage.id): 1,
            ('May %s' % (self.current_year), self.todo_stage.id): 0,
            ('May %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('May %s' % (self.current_year), self.done_stage.id): 5,
            ('May %s' % (self.current_year), self.todo_stage.id): 1,
            ('June %s' % (self.current_year), self.todo_stage.id): 0,
            ('June %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('June %s' % (self.current_year), self.done_stage.id): 5,
            ('June %s' % (self.current_year), self.todo_stage.id): 1,
            ('July %s' % (self.current_year), self.todo_stage.id): 0,
            ('July %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('July %s' % (self.current_year), self.done_stage.id): 5,
            ('July %s' % (self.current_year), self.todo_stage.id): 1,
            ('August %s' % (self.current_year), self.todo_stage.id): 0,
            ('August %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('August %s' % (self.current_year), self.done_stage.id): 5,
            ('August %s' % (self.current_year), self.todo_stage.id): 1,
            ('September %s' % (self.current_year), self.todo_stage.id): 0,
            ('September %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('September %s' % (self.current_year), self.done_stage.id): 5,
            ('September %s' % (self.current_year), self.todo_stage.id): 1,
            ('October %s' % (self.current_year), self.todo_stage.id): 0,
            ('October %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('October %s' % (self.current_year), self.done_stage.id): 5,
            ('October %s' % (self.current_year), self.todo_stage.id): 1,
            ('November %s' % (self.current_year), self.todo_stage.id): 0,
            ('November %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('November %s' % (self.current_year), self.done_stage.id): 5,
            ('November %s' % (self.current_year), self.todo_stage.id): 1,
            ('December %s' % (self.current_year), self.todo_stage.id): 0,
            ('December %s' % (self.current_year), self.in_progress_stage.id): 0,
            ('December %s' % (self.current_year), self.done_stage.id): 5,
            ('December %s' % (self.current_year), self.todo_stage.id): 1,
        }
        self.check_read_group_results(AND([burndown_chart_domain, project_domain]), project_expected_dict)

        # Check that we get the expected results for the complete data of `self.project` & `self.project_2` using an
        # `ilike` in the domain.
        all_projects_domain_with_ilike = OR([project_domain, [('project_id', 'ilike', 'mySearchTag')]])
        project_expected_dict = {key: val if key[1] != self.todo_stage.id else val + 2 for key, val in project_expected_dict.items()}
        self.check_read_group_results(AND([burndown_chart_domain, all_projects_domain_with_ilike]), project_expected_dict)

        date_from, date_to = ('%s-01-01' % (self.current_year - 1), '%s-02-01' % (self.current_year - 1))
        date_and_user_domain = [('date', '>=', date_from), ('date', '<', date_to), ('user_ids', 'ilike', 'ProjectUser')]
        complex_domain_expected_dict = {
            ('January %s' % (self.current_year - 1), self.todo_stage.id): 3,
            ('February %s' % (self.current_year - 1), self.todo_stage.id): 1,
            ('February %s' % (self.current_year - 1), self.in_progress_stage.id): 2,
        }
        complex_domain = AND([burndown_chart_domain, all_projects_domain_with_ilike, date_and_user_domain])
        self.check_read_group_results(complex_domain, complex_domain_expected_dict)

        date_and_user_domain = [('date', '>=', date_from), ('date', '<', date_to), ('user_ids', 'ilike', 'ProjectManager')]
        milestone_domain = [('milestone_id', 'ilike', 'Test')]
        complex_domain = AND([burndown_chart_domain, all_projects_domain_with_ilike, date_and_user_domain, milestone_domain])
        complex_domain_expected_dict = {
            ('January %s' % (self.current_year - 1), self.todo_stage.id): 1,
            ('February %s' % (self.current_year - 1), self.todo_stage.id): 1,
        }
        self.check_read_group_results(complex_domain, complex_domain_expected_dict)


@tagged('-at_install', 'post_install')
class TestBurndownChartTour(HttpCase, TestBurndownChartCommon):

    def test_burndown_chart_tour(self):
        # Test customizing personal stages as a project user
        self.start_tour('/web', 'burndown_chart_tour', login="admin")
