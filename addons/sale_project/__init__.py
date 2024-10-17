# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report

from .models.account_move import AccountMove
from .models.account_move_line import AccountMoveLine
from .models.product_product import ProductProduct
from .models.product_template import ProductTemplate
from .models.project_milestone import ProjectMilestone
from .models.project_project import ProjectProject
from .models.project_task import ProjectTask
from .models.project_task_recurrence import ProjectTaskRecurrence
from .models.res_config_settings import ResConfigSettings
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .models.sale_order_template_line import SaleOrderTemplateLine
from .report.project_report import ReportProjectTaskUser
from .report.sale_report import SaleReport

def _set_allow_billable_in_project(env):
    Project = env['project.project']
    Task = env['project.task']
    projects = Project.search(Project._get_projects_to_make_billable_domain())
    non_billable_projects, = Task._read_group(
        Task._get_projects_to_make_billable_domain([('project_id', 'not in', projects.ids)]),
        [],
        ['project_id:recordset'],
    )[0]
    projects += non_billable_projects
    projects.allow_billable = True


def uninstall_hook(env):
    actions = env['ir.embedded.actions'].search([
        ('parent_res_model', '=', 'project.project'),
        ('python_method', 'in', ['action_open_project_invoices', 'action_view_sos'])
    ])
    actions.domain = [(0, '=', 1)]
