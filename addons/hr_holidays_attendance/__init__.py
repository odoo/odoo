# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import report


def _assign_compensable_as_leave_to_overtime(env):
    """
    Regenerate overtime lines for rulesets containing rules marked as
    compensable as leave.

    This migration ensures that existing overtime lines are updated with the
    correct `compensable_as_leave` value based on their overtime rules.
    """

    overtime_rulesets = env['hr.attendance.overtime.ruleset'].search([
        ('rule_ids.compensable_as_leave', '=', True),
    ])
    for ruleset in overtime_rulesets:
        ruleset.action_regenerate_overtimes()
