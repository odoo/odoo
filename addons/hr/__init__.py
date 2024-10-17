# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import report

from .models.discuss_channel import DiscussChannel
from .models.hr_contract_type import HrContractType
from .models.hr_department import HrDepartment
from .models.hr_departure_reason import HrDepartureReason
from .models.hr_employee import HrEmployee
from .models.hr_employee_base import HrEmployeeBase
from .models.hr_employee_category import HrEmployeeCategory
from .models.hr_employee_public import HrEmployeePublic
from .models.hr_job import HrJob
from .models.hr_work_location import HrWorkLocation
from .models.ir_ui_menu import IrUiMenu
from .models.mail_activity_plan import MailActivityPlan
from .models.mail_activity_plan_template import MailActivityPlanTemplate
from .models.mail_alias import MailAlias
from .models.models import Base
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.resource import ResourceResource
from .report.hr_manager_department_report import HrManagerDepartmentReport
from .wizard.hr_departure_wizard import HrDepartureWizard
from .wizard.mail_activity_schedule import MailActivitySchedule


def _install_hr_localization(env):
    if env["res.company"].search_count([('partner_id.country_id.code', '=', 'MX')], limit=1):
        l10n_mx = env['ir.module.module'].sudo().search([
            ('name', '=', 'l10n_mx_hr'),
            ('state', 'not in', ['installed', 'to install', 'to upgrade']),
        ])
        if l10n_mx:
            l10n_mx.button_install()
