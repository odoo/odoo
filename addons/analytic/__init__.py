# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from .models.analytic_account import AccountAnalyticAccount
from .models.analytic_distribution_model import AccountAnalyticDistributionModel
from .models.analytic_line import AccountAnalyticLine, AnalyticPlanFieldsMixin
from .models.analytic_mixin import AnalyticMixin
from .models.analytic_plan import AccountAnalyticApplicability, AccountAnalyticPlan
from .models.res_config_settings import ResConfigSettings
