# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard
from . import controllers


def _setup_survey_template(env):
    default_template = env['res.company']._get_default_appraisal_survey_template_id()
    env['res.company'].search([]).write({
        'appraisal_survey_template_id': default_template.id,
    })
