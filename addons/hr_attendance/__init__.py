# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

from .models.hr_attendance import HrAttendance
from .models.hr_attendance_overtime import HrAttendanceOvertime
from .models.hr_employee import HrEmployee
from .models.hr_employee_base import HrEmployeeBase
from .models.hr_employee_public import HrEmployeePublic
from .models.res_company import ResCompany
from .models.res_config_settings import ResConfigSettings
from .models.res_users import ResUsers


def post_init_hook(env):
    env['res.company']._check_hr_presence_control(True)


def uninstall_hook(env):
    env['res.company']._check_hr_presence_control(False)
