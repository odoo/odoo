# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.hr_employee import HrEmployee
from .models.hr_employee_public import HrEmployeePublic
from .models.hr_employee_skill import HrEmployeeSkill
from .models.hr_employee_skill_log import HrEmployeeSkillLog
from .models.hr_resume_line import HrResumeLine
from .models.hr_resume_line_type import HrResumeLineType
from .models.hr_skill import HrSkill
from .models.hr_skill_level import HrSkillLevel
from .models.hr_skill_type import HrSkillType
from .models.res_users import ResUsers
from .models.resource_resource import ResourceResource
from .report.hr_employee_cv_report import ReportHr_SkillsReport_Employee_Cv
from .report.hr_employee_skill_report import HrEmployeeSkillReport
from .wizard.hr_employee_cv_wizard import HrEmployeeCvWizard
