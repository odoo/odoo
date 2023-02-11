# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import collections

from odoo import models
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
    _populate_dependencies = ["project.project"]

    def _populate_factories(self):
        project_ids = self.env.registry.populated_models["project.project"]
        stage_ids = self.env.registry.populated_models["project.task.type"]
        def get_project_id(random, **kwargs):
            return random.choice([False, False, False] + project_ids)
        def get_stage_id(random, **kwargs):
            return random.choice([False, False] + stage_ids)
        return [
            ("name", populate.constant('project_task_{counter}')),
            ("sequence", populate.randomize([False] + [i for i in range(1, 101)])),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
            ("color", populate.randomize([False] + [i for i in range(1, 7)])),
            ("kanban_state", populate.randomize(['normal', 'done', 'blocked'])),
            ("project_id", populate.compute(get_project_id)),
            ("stage_id", populate.compute(get_stage_id)),
        ]

    def _populate(self, size):
        records = super()._populate(size)
        # set parent_ids
        self._populate_set_children_tasks(records, size)
        return records

    def _populate_set_children_tasks(self, tasks, size):
        _logger.info('Setting parent tasks')
        rand = populate.Random('project.task+children_generator')
        parents = self.env["project.task"]
        for task in tasks:
            if not rand.getrandbits(4):
                parents |= task
        parent_ids = parents.ids
        tasks -= parents
        parent_childs = collections.defaultdict(lambda: self.env['project.task'])
        for count, task in enumerate(tasks):
            if not rand.getrandbits(4):
                parent_childs[rand.choice(parent_ids)] |= task

        for count, (parent, childs) in enumerate(parent_childs.items()):
            if (count + 1) % 100 == 0:
                _logger.info('Setting parent: %s/%s', count + 1, len(parent_childs))
            childs.write({'parent_id': parent})
