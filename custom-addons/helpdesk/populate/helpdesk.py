# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, Command
from odoo.tools import populate

class HelpdeskStage(models.Model):
    _inherit = "helpdesk.stage"
    _populate_sizes = {"small": 10, "medium": 50, "large": 500}

    def _populate_factories(self):
        return [
            ("name", populate.constant('stage_{counter}')),
            ("sequence", populate.randomize([i for i in range(1, 101)])),
            ("fold", populate.randomize([True, False], [0.3, 0.7], '{counter}')),
        ]

class HelpdeskTeam(models.Model):
    _inherit = "helpdesk.team"
    _populate_dependencies = ["res.company", "helpdesk.stage"]
    _populate_sizes = {"small": 10, "medium": 50, "large": 1000}

    def _populate_factories(self):
        company_ids = self.env.registry.populated_models["res.company"]
        stage_ids = self.env.registry.populated_models["helpdesk.stage"]

        def get_company_id(random, **kwargs):
            return random.choice(company_ids)

        def get_stage_ids(random, **kwargs):
            return [
                Command.set([
                    random.choice(stage_ids)
                    for i in range(random.choice([j for j in range(1, 10)]))
                ])
            ]

        return [
            ("name", populate.constant('team_{counter}')),
            ("stage_ids", populate.compute(get_stage_ids)),
            ("company_id", populate.compute(get_company_id)),
            ("use_sla", populate.constant(True)),
        ]

class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"
    _populate_sizes = {"small": 500, "medium": 5000, "large": 50000}
    _populate_dependencies = ["helpdesk.team", "helpdesk.sla"]

    def _populate_factories(self):
        stages_per_team = {
            team.id: ids
            for team, ids in self.env['helpdesk.stage']._read_group(
                domain=[
                    ('id', 'in', self.env.registry.populated_models["helpdesk.stage"]),
                    ('team_ids', 'in', self.env.registry.populated_models["helpdesk.team"]),
                ],
                groupby=['team_ids'],
                aggregates=['id:array_agg'],
            )
        }
        team_ids = list(stages_per_team)

        def get_stage_id(random, **kwargs):
            return random.choice(stages_per_team[kwargs['values']['team_id']])

        def get_team_id(random, **kwargs):
            return random.choice(team_ids)

        return [
            ("name", populate.constant('ticket_{counter}')),
            ("team_id", populate.compute(get_team_id)),
            ("stage_id", populate.compute(get_stage_id)),
            ("active", populate.randomize([True, False], [0.8, 0.2])),
            ("priority", populate.randomize([str(i) for i in range(0, 4)])),
        ]

class HelpdeskSLA(models.Model):
    _inherit = "helpdesk.sla"
    _populate_sizes = {"small": 10, "medium": 100, "large": 1000}
    _populate_dependencies = ["helpdesk.team"]

    def _populate_factories(self):
        stages_per_team = {
            team.id: ids
            for team, ids in self.env['helpdesk.stage']._read_group(
                domain=[
                    ('id', 'in', self.env.registry.populated_models["helpdesk.stage"]),
                    ('team_ids', 'in', self.env.registry.populated_models["helpdesk.team"]),
                ],
                groupby=['team_ids'],
                aggregates=['id:array_agg'],
            )
        }
        team_ids = list(stages_per_team)

        def get_team_id(random, **kwargs):
            return random.choice(team_ids)

        def get_stage_id(random, **kwargs):
            return random.choice(stages_per_team[kwargs['values']['team_id']])

        return [
            ("name", populate.constant('sla_{counter}')),
            ("team_id", populate.compute(get_team_id)),
            ("priority", populate.randomize([str(i) for i in range(0, 4)])),
            ("stage_id", populate.compute(get_stage_id)),
            ("time", populate.randfloat(0, 40)),
        ]
