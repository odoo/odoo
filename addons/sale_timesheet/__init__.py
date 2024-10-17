# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import controllers
from . import models
from . import wizard
from . import report

from .models.account_move import AccountMove
from .models.account_move_line import AccountMoveLine
from .models.hr_employee import HrEmployee
from .models.hr_timesheet import AccountAnalyticLine
from .models.product_product import ProductProduct
from .models.product_template import ProductTemplate
from .models.project_project import ProjectProject
from .models.project_sale_line_employee_map import ProjectSaleLineEmployeeMap
from .models.project_task import ProjectTask
from .models.project_update import ProjectUpdate
from .models.res_config_settings import ResConfigSettings
from .models.sale_order import SaleOrder
from .models.sale_order_line import SaleOrderLine
from .report.project_report import ReportProjectTaskUser
from .report.timesheets_analysis_report import TimesheetsAnalysisReport
from .wizard.project_create_invoice import ProjectCreateInvoice
from .wizard.sale_make_invoice_advance import SaleAdvancePaymentInv


def uninstall_hook(env):
    env.ref("account.account_analytic_line_rule_billing_user").write({'domain_force': "[(1, '=', 1)]"})

def _sale_timesheet_post_init(env):
    products = env['product.template'].search([
        ('type', '=', 'service'),
        ('service_tracking', 'in', ['no', 'task_global_project', 'task_in_project', 'project_only']),
        ('invoice_policy', '=', 'order'),
        ('service_type', '=', 'manual'),
    ])

    for product in products:
        product.service_type = 'timesheet'
        product._compute_service_policy()
