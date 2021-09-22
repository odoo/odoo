# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from freezegun import freeze_time
from datetime import datetime

from odoo import Command
from odoo.tests.common import TransactionCase


class TestBurndownChart(TransactionCase):
    def set_create_date(self, table, res_id, create_date):
        self.env.cr.execute("UPDATE {} SET create_date=%s WHERE id=%s".format(table), (create_date, res_id))

    def test_burndown_chart(self):
        current_year = datetime.now().year
        create_date = datetime(current_year - 1, 1, 1)
        kanban_state_vals = {
            "legend_blocked": 'Blocked',
            "legend_done": 'Ready',
            "legend_normal": 'In Progress'
        }
        Stage = self.env['project.task.type']
        todo_stage = Stage.create({
            'sequence': 1,
            'name': 'TODO',
            **kanban_state_vals,
        })
        self.set_create_date('project_task_type', todo_stage.id, create_date)
        in_progress_stage = Stage.create({
            'sequence': 10,
            'name': 'In Progress',
            **kanban_state_vals,
        })
        self.set_create_date('project_task_type', in_progress_stage.id, create_date)
        testing_stage = Stage.create({
            'sequence': 20,
            'name': 'Testing',
            **kanban_state_vals,
        })
        self.set_create_date('project_task_type', testing_stage.id, create_date)
        done_stage = Stage.create({
            'sequence': 30,
            'name': 'Done',
            **kanban_state_vals,
        })
        self.set_create_date('project_task_type', done_stage.id, create_date)
        stages = todo_stage + in_progress_stage + testing_stage + done_stage
        project = self.env['project.project'].create({
            'name': 'Burndown Chart Test',
            'privacy_visibility': 'employees',
            'alias_name': 'project+burndown_chart',
            'type_ids': [Command.link(stage_id) for stage_id in stages.ids],
        })
        self.set_create_date('project_project', project.id, create_date)
        project.invalidate_cache()
        task_a = self.env['project.task'].create({
            'name': 'Task A',
            'priority': 0,
            'project_id': project.id,
            'stage_id': todo_stage.id,
        })
        self.set_create_date('project_task', task_a.id, create_date)
        task_b = task_a.copy({
            'name': 'Task B',
        })
        self.set_create_date('project_task', task_b.id, create_date)
        task_c = task_a.copy({
            'name': 'Task C',
        })
        self.set_create_date('project_task', task_c.id, create_date)
        task_d = task_a.copy({
            'name': 'Task D',
        })
        self.set_create_date('project_task', task_d.id, create_date)
        task_e = task_a.copy({
            'name': 'Task E',
        })
        self.set_create_date('project_task', task_e.id, create_date)

        # Create a new task to check if a task without changing its stage is taken into account
        task_f = self.env['project.task'].create({
            'name': 'Task F',
            'priority': 0,
            'project_id': project.id,
            'stage_id': todo_stage.id,
        })
        self.set_create_date('project_task', task_f.id, datetime(current_year - 1, 12, 20))

        # Precommit to have the records in db and allow to rollback at the end of test
        self.env.cr.flush()

        with freeze_time('%s-02-10' % (current_year - 1)):
            (task_a + task_b).write({'stage_id': in_progress_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-02-20' % (current_year - 1)):
            task_c.write({'stage_id': in_progress_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-03-15' % (current_year - 1)):
            (task_d + task_e).write({'stage_id': in_progress_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-04-10' % (current_year - 1)):
            (task_a + task_b).write({'stage_id': testing_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-05-12' % (current_year - 1)):
            task_c.write({'stage_id': testing_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-06-25' % (current_year - 1)):
            task_d.write({'stage_id': testing_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-07-25' % (current_year - 1)):
            task_e.write({'stage_id': testing_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-08-01' % (current_year - 1)):
            task_a.write({'stage_id': done_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-09-10' % (current_year - 1)):
            task_b.write({'stage_id': done_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-10-05' % (current_year - 1)):
            task_c.write({'stage_id': done_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-11-25' % (current_year - 1)):
            task_d.write({'stage_id': done_stage.id})
            self.env.cr.flush()

        with freeze_time('%s-12-12' % (current_year - 1)):
            task_e.write({'stage_id': done_stage.id})
            self.env.cr.flush()

        read_group_result = self.env['project.task.burndown.chart.report'].with_context(fill_temporal=True).read_group([('project_id', '=', project.id), ('display_project_id', '!=', False)], ['date', 'stage_id', 'nb_tasks'], ['date:month', 'stage_id'], lazy=False)
        read_group_result_dict = {(res['date:month'], res['stage_id'][0]): res['nb_tasks'] for res in read_group_result}
        stages_dict = {stage.id: stage.name for stage in stages}
        expected_dict = {
            ('January %s' % (current_year - 1), todo_stage.id): 5,
            ('February %s' % (current_year - 1), todo_stage.id): 2,
            ('February %s' % (current_year - 1), in_progress_stage.id): 3,
            ('March %s' % (current_year - 1), in_progress_stage.id): 5,
            ('April %s' % (current_year - 1), in_progress_stage.id): 3,
            ('April %s' % (current_year - 1), testing_stage.id): 2,
            ('May %s' % (current_year - 1), in_progress_stage.id): 2,
            ('May %s' % (current_year - 1), testing_stage.id): 3,
            ('June %s' % (current_year - 1), in_progress_stage.id): 1,
            ('June %s' % (current_year - 1), testing_stage.id): 4,
            ('July %s' % (current_year - 1), testing_stage.id): 5,
            ('August %s' % (current_year - 1), testing_stage.id): 4,
            ('August %s' % (current_year - 1), done_stage.id): 1,
            ('September %s' % (current_year - 1), testing_stage.id): 3,
            ('September %s' % (current_year - 1), done_stage.id): 2,
            ('October %s' % (current_year - 1), testing_stage.id): 2,
            ('October %s' % (current_year - 1), done_stage.id): 3,
            ('November %s' % (current_year - 1), testing_stage.id): 1,
            ('November %s' % (current_year - 1), done_stage.id): 4,
            ('December %s' % (current_year - 1), done_stage.id): 5,
            ('December %s' % (current_year - 1), todo_stage.id): 1,
            ('January %s' % (current_year), done_stage.id): 5,
            ('January %s' % (current_year), todo_stage.id): 1,
        }
        for (month, stage_id), nb_tasks in read_group_result_dict.items():
            # when we don't found any record in the dict then we are in the current_year
            # and the number of tasks should always be 5 in Done stage and 1 in Todo Stage
            # since we have created the last task without changing its stage.
            expected_nb_tasks = expected_dict.get((month, stage_id), 5 if stage_id != todo_stage.id else 1)
            self.assertEqual(
                nb_tasks,
                expected_nb_tasks,
                'In %s, the number of tasks should be equal to %s in %s stage.' % (month, expected_nb_tasks, stages_dict.get(stage_id, 'Unknown'))
            )
