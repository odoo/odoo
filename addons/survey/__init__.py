# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report
from . import wizard

from .models.badge import GamificationBadge
from .models.challenge import GamificationChallenge
from .models.res_partner import ResPartner
from .models.survey_question import SurveyQuestion, SurveyQuestionAnswer
from .models.survey_survey_template import SurveySurvey
from .models.survey_user_input import SurveyUser_Input, SurveyUser_InputLine
from .wizard.survey_invite import SurveyInvite
