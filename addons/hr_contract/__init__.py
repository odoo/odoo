# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .models import (
    HrContract, HrEmployee, HrEmployeeBase, HrEmployeePublic,
    HrPayrollStructureType, IrUiMenu, ResCompany, ResConfigSettings, ResUsers, ResourceCalendar,
    ResourceCalendarLeaves, ResourceResource,
)
from .report import HrContractHistory
from .wizard import HrDepartureWizard, MailActivitySchedule
