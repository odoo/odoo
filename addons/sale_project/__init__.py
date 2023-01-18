# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import controllers
from . import report

def _set_allow_billable_in_project(env):
    projects = env['project.project'].search([('partner_id', '!=', False), ('allow_billable', '=', False)])
    projects.allow_billable = True
