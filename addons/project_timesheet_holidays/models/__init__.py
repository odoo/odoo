# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .res_company import ResCompany  # has to be before hr_holidays to create needed columns on res.company
from .account_analytic import AccountAnalyticLine
from .hr_holidays import HrLeave, HrLeaveType
from .project_task import ProjectTask
from .res_config_settings import ResConfigSettings
from .resource_calendar_leaves import ResourceCalendarLeaves
from .hr_employee import HrEmployee
