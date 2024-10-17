# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report
from . import wizard

from .models.hr_contract import HrContract
from .models.hr_employee import HrEmployee, HrEmployeeBase, HrEmployeePublic
from .models.hr_payroll_structure_type import HrPayrollStructureType
from .models.ir_ui_menu import IrUiMenu
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_users import ResUsers
from .models.resource import ResourceCalendar
from .models.resource_calendar_leaves import ResourceCalendarLeaves
from .models.resource_resource import ResourceResource
from .report.hr_contract_history import HrContractHistory
from .wizard.hr_departure_wizard import HrDepartureWizard
from .wizard.mail_activity_schedule import MailActivitySchedule
