# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.tools import populate

class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"
    _populate_sizes = {"small": 500, "medium": 5000, "large": 50000}
    _populate_dependencies = ["project.project", "project.task", "hr.employee"]


    def _populate_factories(self):
        projects_groups = self.env['project.project']._read_group(
            domain=[('id', 'in', self.env.registry.populated_models["project.project"])],
            groupby=['company_id'],
            aggregates=['id:array_agg'],
        )
        project_ids = []
        projects_per_company = defaultdict(list)
        for company, ids in projects_groups:
            project_ids += ids
            projects_per_company[company.id] = ids

        tasks_per_project = {
            project.id: ids
            for project, ids in self.env['project.task']._read_group(
                domain=[
                    ('id', 'in', self.env.registry.populated_models["project.task"]),
                    ('project_id', 'in', project_ids),
                ],
                groupby=['project_id'],
                aggregates=['id:array_agg'],
            )
        }
        employees_per_company = {
            company.id: ids
            for company, ids in self.env['hr.employee']._read_group(
                domain=[('id', 'in', self.env.registry.populated_models["hr.employee"])],
                groupby=['company_id'],
                aggregates=['id:array_agg'],
            )
        }
        # Companies with projects and employees only
        company_ids = list(
            set(self.env.registry.populated_models["res.company"])\
          & set(employees_per_company.keys())\
          & set(projects_per_company.keys())
        )

        def get_company_id(random, **kwargs):
            return random.choice(company_ids)

        def get_project_id(random, **kwargs):
            return random.choice(projects_per_company[kwargs['values']['company_id']])

        def get_task_id(random, **kwargs):
            task_ids = tasks_per_project[kwargs['values']['project_id']]
            return random.choice(task_ids + [False] * (len(task_ids) // 3))

        def get_employee_id(random, **kwargs):
            return random.choice(employees_per_company[kwargs['values']['company_id']])

        return [
            ("date", populate.randdatetime(relative_before=relativedelta(months=-3), relative_after=relativedelta(months=3))),
            ('unit_amount', populate.randfloat(0.0, 8.0)),
            ("company_id", populate.compute(get_company_id)),
            ("project_id", populate.compute(get_project_id)),
            ("task_id", populate.compute(get_task_id)),
            ("employee_id", populate.compute(get_employee_id)),
        ]
