# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def _validate_existing_work_entry(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['hr.work.entry'].search([])._check_if_error()
