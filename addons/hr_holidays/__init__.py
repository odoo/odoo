# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    CalendarEvent, HrDepartment, HrEmployee, HrEmployeeBase, HrLeave,
    HrLeaveAccrualLevel, HrLeaveAccrualPlan, HrLeaveAllocation, HrLeaveMandatoryDay, HrLeaveType,
    MailMessageSubtype, ResPartner, ResUsers, ResourceCalendar, ResourceCalendarLeaves,
)
from .report import (
    HrLeaveEmployeeTypeReport, HrLeaveReport, HrLeaveReportCalendar,
    ReportHr_HolidaysReport_Holidayssummary,
)
from .wizard import (
    HrDepartureWizard, HrHolidaysCancelLeave, HrHolidaysSummaryEmployee,
    HrLeaveAllocationGenerateMultiWizard, HrLeaveGenerateMultiWizard,
)

from odoo import api, SUPERUSER_ID

def _hr_holiday_post_init(env):
    french_companies = env['res.company'].search_count([('partner_id.country_id.code', '=', 'FR')])
    if french_companies:
        env['ir.module.module'].search([
            ('name', '=', 'l10n_fr_hr_work_entry_holidays'),
            ('state', '=', 'uninstalled')
        ]).sudo().button_install()
