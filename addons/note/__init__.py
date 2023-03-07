# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models

def _init_onboarding_todo(env):
    existing_users = env['res.users'].search([('partner_share', '=', False)])
    existing_users._generate_onboarding_todo()
