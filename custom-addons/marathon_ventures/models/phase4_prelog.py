# -*- coding: utf-8 -*-
"""Phase 4 — Prelog Data Mirror enhancements (SF Workflow 21, 24).

Adds clearance-status booleans for the Prelog Dashboard, validation when
archiving prelog rows with a removal_reason, and an `action_remove_prelog`
button that flips the row to archived with the chosen reason.
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MvPrelogDataMirrorPhase4(models.Model):
    _name = 'mv.prelog_data_mirror'
    _inherit = ['mv.prelog_data_mirror']

    archived = fields.Boolean(
        string='Archived (Removed)',
        default=False,
        copy=False,
        help='Set by the Prelog Removal Process. Removed rows are excluded from KPIs.',
    )
    archived_date = fields.Datetime(string='Removed On', readonly=True, copy=False)
    archived_by_id = fields.Many2one('res.users', string='Removed By', readonly=True, copy=False)

    @api.constrains('archived', 'removal_reason')
    def _check_archived_has_reason(self):
        for r in self:
            if r.archived and not r.removal_reason:
                raise ValidationError(_(
                    "When archiving a Prelog row you MUST pick a Removal Reason "
                    "(Overrun / Out of Rotation / Not Booked / Cancelled / Hiatused / CIA / Other)."
                ))

    def action_remove_prelog(self):
        """Mark this Prelog Data Mirror row as removed."""
        for r in self:
            if not r.removal_reason:
                raise UserError(_("Set a Removal Reason before removing the prelog row."))
            r.archived = True
            r.archived_date = fields.Datetime.now()
            r.archived_by_id = self.env.user.id
            r.message_post(body=_("Prelog row removed. Reason: %s") % dict(r._fields['removal_reason'].selection).get(r.removal_reason, '—'))
        return True

    def action_restore_prelog(self):
        """Undo a removal."""
        for r in self:
            r.archived = False
            r.archived_date = False
            r.archived_by_id = False
            r.message_post(body=_("Prelog row restored."))
        return True
