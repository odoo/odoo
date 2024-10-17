# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from odoo import api, SUPERUSER_ID

from .models.calendar_event import CalendarEvent
from .models.hr_department import HrDepartment
from .models.hr_employee import HrEmployee
from .models.hr_employee_base import HrEmployeeBase
from .models.hr_leave import HrLeave
from .models.hr_leave_accrual_plan import HrLeaveAccrualPlan
from .models.hr_leave_accrual_plan_level import HrLeaveAccrualLevel
from .models.hr_leave_allocation import HrLeaveAllocation
from .models.hr_leave_mandatory_day import HrLeaveMandatoryDay
from .models.hr_leave_type import HrLeaveType
from .models.mail_message_subtype import MailMessageSubtype
from .models.res_partner import ResPartner
from .models.res_users import ResUsers
from .models.resource import ResourceCalendar, ResourceCalendarLeaves
from .report.holidays_summary_report import ReportHr_HolidaysReport_Holidayssummary
from .report.hr_leave_employee_type_report import HrLeaveEmployeeTypeReport
from .report.hr_leave_report import HrLeaveReport
from .report.hr_leave_report_calendar import HrLeaveReportCalendar
from .wizard.hr_departure_wizard import HrDepartureWizard
from .wizard.hr_holidays_cancel_leave import HrHolidaysCancelLeave
from .wizard.hr_holidays_summary_employees import HrHolidaysSummaryEmployee
from .wizard.hr_leave_allocation_generate_multi_wizard import (
        HrLeaveAllocationGenerateMultiWizard,
)
from .wizard.hr_leave_generate_multi_wizard import HrLeaveGenerateMultiWizard

def _hr_holiday_post_init(env):
    french_companies = env['res.company'].search_count([('partner_id.country_id.code', '=', 'FR')])
    if french_companies:
        env['ir.module.module'].search([
            ('name', '=', 'l10n_fr_hr_work_entry_holidays'),
            ('state', '=', 'uninstalled')
        ]).sudo().button_install()
