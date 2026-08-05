# -*- coding: utf-8 -*-
"""Phase 24 - Store the picked program-daypart LABEL on each schedule.

Business goal: when a schedule is created from the Units Report, we
already snapshot Start Time / End Time / Days Allowed onto the
schedule. We now also snapshot the DAYPART LABEL so the schedule
carries the full daypart context independently of the Program
record.

The primary field is `program_daypart` (Char) - stores the label
directly, works for both program-configured and hardcoded-fallback
dayparts.

The two legacy fields (`program_daypart_id`, `daypart_label`) are
kept as inert placeholders so that during an upgrade, any stale
ir.ui.view record in the database that still references them
passes view validation. The current view arch on disk no longer
references either field - once the upgrade succeeds, Odoo
overwrites the DB view arch with the clean version and the
placeholders become truly unused (safe to remove in a future
migration).
"""
from odoo import models, fields


class MvSchedulesProgramDaypart(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    # Primary field - the label string the save flow writes.
    program_daypart = fields.Char(
        string='Program Daypart',
        help='The daypart label captured when this schedule was saved '
             'from the Units Report. Works both for program-configured '
             'dayparts (uses the daypart record\'s name) and the '
             'hardcoded fallback (uses the standard label - Daytime, '
             'Prime, Early Morning, ...). Populated by the Units '
             'Report save flow; safe to leave blank on legacy rows.',
    )

    # ------------------------------------------------------------------
    # Legacy placeholders. Kept so stale DB view arches referencing
    # these fields validate cleanly during upgrade. Not shown on any
    # current view (see phase9_schedule_layout_views.xml).
    # ------------------------------------------------------------------
    program_daypart_id = fields.Many2one(
        comodel_name='mv.program.daypart',
        string='Program Daypart (legacy)',
        ondelete='set null',
        index=True,
        help='DEPRECATED: replaced by the program_daypart Char field. '
             'Kept as a placeholder so upgrade view validation passes.',
    )
    daypart_label = fields.Char(
        string='Daypart Label (legacy)',
        store=False,
        readonly=True,
        help='DEPRECATED: unused. Placeholder for legacy view validation.',
    )
