# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import collections

from odoo import models, Command
from odoo.tools import populate

_logger = logging.getLogger(__name__)

class ProjectStage(models.Model):
    _inherit = "project.task.type"
    _populate_sizes = {"small": 10, "medium": 50, "large": 500}

    def _populate_factories(self):
        return [
            ("name", populate.constant('stage_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("description", populate.constant('project_stage_description_{counter}')),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
            ("fold", populate.randomize([True, False], [0.9, 0.1]))
        ]

class ProjectProject(models.Model):
    _inherit = "project.project"
    _populate_sizes = {"small": 10, "medium": 50, "large": 1000}
    _populate_dependencies = ["res.company", "project.task.type"]

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"]
        stage_ids = self.env.registry.populated_models["project.task.type"]

        def get_company_id(random, **kwargs):
            return random.choice(company_ids)
            # user_ids from company.user_ids ?
            # Also add a partner_ids on res_company ?

        def get_stage_ids(random, **kwargs):
            return [
                (6, 0, [
                    random.choice(stage_ids)
                    for i in range(random.choice([j for j in range(1, 10)]))
                ])
            ]

        return [
            ("name", populate.constant('project_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
            ("company_id", populate.compute(get_company_id)),
            ("type_ids", populate.compute(get_stage_ids)),
            ('color', populate.randomize([False] + [i for i in range(1, 7)])),
            # TODO user_id but what about multi-company coherence ??
        ]


class ProjectTask(models.Model):
    _inherit = "project.task"
    _populate_sizes = {"small": 500, "medium": 5000, "large": 50000}
    _populate_dependencies = ["project.project", "res.partner", "res.users"]

    def _populate_factories(self):
        project_ids = self.env.registry.populated_models["project.project"]
        stage_ids = self.env.registry.populated_models["project.task.type"]
        user_ids = self.env.registry.populated_models['res.users']
        partner_ids_per_company_id = {
            company.id: ids
            for company, ids in self.env['res.partner']._read_group(
                [('company_id', '!=', False), ('id', 'in', self.env.registry.populated_models["res.partner"])],
                ['company_id'],
                ['id:array_agg'],
            )
        }
        company_id_per_project_id = {
            record['id']: record['company_id']
            for record in self.env['project.project'].search_read(
                [('company_id', '!=', False), ('id', 'in', self.env.registry.populated_models["project.project"])],
                ['company_id'],
                load=False
            )
        }
        partner_ids_per_project_id = {
            project_id: partner_ids_per_company_id[company_id]
            for project_id, company_id in company_id_per_project_id.items()
        }
        def get_project_id(random, **kwargs):
            return random.choice([False, False, False] + project_ids)
        def get_stage_id(random, **kwargs):
            return random.choice([False, False] + stage_ids)
        def get_partner_id(random, **kwargs):
            project_id = kwargs['values'].get('project_id')
            partner_ids = partner_ids_per_project_id.get(project_id, False)
            return partner_ids and random.choice(partner_ids + [False] * len(partner_ids))
        def get_user_ids(values, counter, random):
            return [Command.set([random.choice(user_ids) for i in range(random.randint(0, 3))])]

        return [
            ("name", populate.constant('project_task_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
            ("color", populate.randomize([False] + [i for i in range(1, 7)])),
            ("state", populate.randomize(['01_in_progress', '03_approved', '02_changes_requested', '1_done', '1_canceled'])),
            ("project_id", populate.compute(get_project_id)),
            ("stage_id", populate.compute(get_stage_id)),
            ('partner_id', populate.compute(get_partner_id)),
            ('user_ids', populate.compute(get_user_ids)),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        # set parent_ids
        self._populate_set_children_tasks(records)
        return records

    def _populate_set_children_tasks(self, tasks):
        _logger.info('Setting parent tasks')
        rand = populate.Random('project.task+children_generator')
        task_ids_per_company = collections.defaultdict(set)
        for task in tasks:
            if task.project_id:
                task_ids_per_company[task.company_id].add(task.id)

        for task_ids in task_ids_per_company.values():
            parent_ids = set()
            for task_id in task_ids:
                if not rand.getrandbits(4):
                    parent_ids.add(task_id)
            child_ids = task_ids - parent_ids
            parent_ids = list(parent_ids)

            child_ids_per_parent_id = collections.defaultdict(set)
            for child_id in child_ids:
                if not rand.getrandbits(4):
                    child_ids_per_parent_id[rand.choice(parent_ids)].add(child_id)

            for count, (parent_id, child_ids) in enumerate(child_ids_per_parent_id.items()):
                if (count + 1) % 100 == 0:
                    _logger.info('Setting parent: %s/%s', count + 1, len(child_ids_per_parent_id))
                self.browse(child_ids).write({'parent_id': parent_id})
