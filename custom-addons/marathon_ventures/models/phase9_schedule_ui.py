# -*- coding: utf-8 -*-
"""Phase 9 - Schedule UI helpers.

Mirrors the Deal redesign: transient toggle for the collapsed Advanced
section, plus two display-only helpers ("Additional Weeks" / "End Week
auto-filled") that approximate the mockup without requiring a separate
wizard step.
"""
from datetime import timedelta
from odoo import models, fields, api


class MvScheduleUiPhase9(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    # UI-only flag - default False = Advanced section collapsed.
    show_advanced_schedule = fields.Boolean(
        string='Show Advanced',
        default=False,
        store=False,
        copy=False,
    )

    # Additional Weeks - a hint count the planner can type. NOT stored;
    # the existing mv.schedule.additional.wizard is the real mechanism
    # for cloning N weekly schedules. This field exists so the create
    # form matches the mockup layout (Start Week | Additional Weeks |
    # End Week auto).
    additional_weeks = fields.Integer(
        string='Additional Weeks',
        default=0,
        store=False,
        copy=False,
        help='UI hint only. Use the "Additional Schedules" wizard to '
             'actually clone N weekly schedules after this one is saved.',
    )

    # End Week (auto) - computed from week + additional_weeks.
    end_week_auto = fields.Date(
        string='End Week (auto)',
        compute='_compute_end_week_auto',
        store=False,
        readonly=True,
        help='Auto-calculated as Start Week + Additional Weeks. Display only.',
    )

    # Program - related Many2one through deal_parent.program. Lets the
    # Targeting section show Network / Daypart / Program in one row
    # without forcing the planner to open the Deal record to see which
    # program the schedule belongs to.
    program = fields.Many2one(
        related='deal_parent.program',
        string='Program',
        store=True,
        readonly=True,
    )

    @api.depends('week', 'additional_weeks')
    def _compute_end_week_auto(self):
        for rec in self:
            if rec.week:
                weeks = rec.additional_weeks or 0
                rec.end_week_auto = rec.week + timedelta(weeks=weeks)
            else:
                rec.end_week_auto = False

    def action_toggle_advanced_schedule(self):
        for rec in self:
            rec.show_advanced_schedule = not rec.show_advanced_schedule
        return False

    # NOTE: action_cancel_schedule was previously overridden here to
    # redirect to the schedules list view. That override completely
    # masked phase1_schedule.action_cancel_schedule which actually
    # flips status -> 'canceled'. Removing the override so clicking
    # the "Cancel Schedule" button cancels the record in place; the
    # user stays on the form and sees the status change to Canceled.
