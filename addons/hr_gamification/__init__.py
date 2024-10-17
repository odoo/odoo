# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.gamification import GamificationBadge, GamificationBadgeUser
from .models.hr_employee import HrEmployeeBase
from .models.res_users import ResUsers
from .wizard.gamification_badge_user_wizard import GamificationBadgeUserWizard
