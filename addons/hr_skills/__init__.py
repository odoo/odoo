# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    HrEmployee, HrEmployeePublic, HrEmployeeSkill, HrEmployeeSkillLog,
    HrResumeLine, HrResumeLineType, HrSkill, HrSkillLevel, HrSkillType, ResUsers,
    ResourceResource,
)
from .report import HrEmployeeSkillReport, ReportHr_SkillsReport_Employee_Cv
from .wizard import HrEmployeeCvWizard
