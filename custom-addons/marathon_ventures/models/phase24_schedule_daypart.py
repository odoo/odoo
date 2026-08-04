# -*- coding: utf-8 -*-
"""Phase 24 - Store the picked program-daypart on each schedule.

Business goal: when a schedule is created from the Units Report, we
already snapshot Start Time / End Time / Days Allowed onto the
schedule. We now also snapshot the DAYPART itself so the schedule
carries the full daypart context independently of the Program
record.

Why a new field instead of reusing mv.schedules.mgm_hd_daypart:
mgm_hd_daypart is a Selection with a huge hardcoded list of
Salesforce cable-daypart codes (em_ms_4a_9a, da_ms_8a_6p, ...)
already populated by the SF migration and visible on multiple
schedule forms. Repurposing it would break existing data + UI.

The link is a Many2one to mv.program.daypart. When the row's
daypart is a hardcoded one (early_morning, weekday, prime, ...
i.e. not a program-defined daypart), this field stays empty and
the daypart is inferable from the schedule's start_time/end_time
via the existing _guess_daypart helper.
"""
from odoo import models, fields


class MvSchedulesProgramDaypart(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    program_daypart_id = fields.Many2one(
        comodel_name='mv.program.daypart',
        string='Program Daypart',
        ondelete='set null',
        index=True,
        help='The Program-defined daypart selected on this schedule row '
             'in the Units Report. Empty when the row used a hardcoded '
             'daypart (Early Morning, Weekday, Prime, etc.). The '
             'schedule always keeps its own Start Time / End Time / '
             'Days Allowed, so the daypart config is preserved even '
             'if this link is cleared.',
    )
