# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import report


def _populate_skills_for_confirmed(env):
    confirmed_appraisals = env['hr.appraisal'].search([('state', '=', 'pending'), ('skill_ids', '=', False)])
    confirmed_appraisals._copy_skills_when_confirmed()
