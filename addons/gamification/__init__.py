# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

from .models.gamification_badge import GamificationBadge
from .models.gamification_badge_user import GamificationBadgeUser
from .models.gamification_challenge import GamificationChallenge
from .models.gamification_challenge_line import GamificationChallengeLine
from .models.gamification_goal import GamificationGoal
from .models.gamification_goal_definition import GamificationGoalDefinition
from .models.gamification_karma_rank import GamificationKarmaRank
from .models.gamification_karma_tracking import GamificationKarmaTracking
from .models.res_users import ResUsers
from .wizard.grant_badge import GamificationBadgeUserWizard
from .wizard.update_goal import GamificationGoalWizard
