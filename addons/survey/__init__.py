# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from .models import (
    GamificationBadge, GamificationChallenge, ResPartner, SurveyQuestion,
    SurveyQuestionAnswer, SurveySurvey, SurveyUser_Input, SurveyUser_InputLine,
)
from . import report
from .wizard import SurveyInvite
