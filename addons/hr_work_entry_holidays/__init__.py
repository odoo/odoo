# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models


def _validate_existing_work_entry(env):
    env['hr.work.entry'].search([])._check_if_error()
