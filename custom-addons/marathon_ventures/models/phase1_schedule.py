# -*- coding: utf-8 -*-
"""Phase 1 — Schedule lifecycle additions on top of the auto-generated mv.schedules.

What this layer adds:
  * Monday-only validation on `week` (SF Workflow 2 step 2 — schedules must start on a Monday).
  * Computed `total_dollars` = rate × units_available  (Double Check Report rollup).
  * Computed `equiv_30` = units_available × (deal.length / 30)  (OPS Dashboard inputs).
  * action_cancel_schedule / action_uncancel_schedule (one-click status flip).
  * Default Status = 'sold' on create.
  * Default Networks/Length pulled from deal parent if not provided.
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MvSchedulesPhase1(models.Model):
    _inherit = 'mv.schedules'

    # ------------------------------------------------------------------
    # Phase 1 computed rollups
    # ------------------------------------------------------------------
    total_dollars = fields.Monetary(
        string='Total Dollars',
        compute='_compute_total_dollars',
        store=True,
        currency_field='currency_id',
        help='Rate × Units Available — used in the Double Check Report.',
    )
    equiv_30 = fields.Float(
        string='Equiv :30',
        compute='_compute_equiv_30',
        store=True,
        digits=(17, 2),
        help='units_available × (deal.length / 30) — used by OPS Dashboard.',
    )

    @api.depends('rate', 'units_available')
    def _compute_total_dollars(self):
        for s in self:
            rate = s.rate or 0.0
            units = s.units_available or 0.0
            s.total_dollars = rate * units

    @api.depends('units_available', 'deal_parent.length')
    def _compute_equiv_30(self):
        for s in self:
            length_key = (s.deal_parent.length if s.deal_parent else '') or ''
            # SF length is a Selection like 'v_30', 'v_60', 'v_120' — strip prefix to int
            try:
                length = int((length_key or '').replace('v_','')) if length_key else 0
            except Exception:
                length = 0
            units = s.units_available or 0.0
            s.equiv_30 = (units * (length / 30.0)) if length else units

    # ------------------------------------------------------------------
    # Validations (Workflow 2 — week must be a Monday; rate/units non-negative)
    # ------------------------------------------------------------------
    @api.constrains('week')
    def _check_week_is_monday(self):
        for s in self:
            if s.week and s.week.weekday() != 0:  # 0 == Monday
                raise ValidationError(_(
                    "Schedule Week must be a Monday (you entered %s, a %s)."
                ) % (s.week, s.week.strftime('%A')))

    @api.constrains('rate', 'units_available')
    def _check_non_negative(self):
        for s in self:
            if s.rate is not None and s.rate < 0:
                raise ValidationError(_("Rate cannot be negative."))
            if s.units_available is not None and s.units_available < 0:
                raise ValidationError(_("Units Available cannot be negative."))

    # ------------------------------------------------------------------
    # Defaults — status='sold'; networks default from parent program if available.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('status', 'sold')
        return super().create(vals_list)

    @api.onchange('deal_parent')
    def _onchange_deal_parent_fill_networks(self):
        for s in self:
            if s.deal_parent and s.deal_parent.program and not s.networks:
                # Networks is a Selection on mv.schedules; we can only set it if the
                # program's name matches one of the Selection keys.  Otherwise we
                # leave it for the user to pick — flagged as TODO open question #1
                # in the workflow map.
                key = (s.deal_parent.program.display_name or '').lower().replace(' ', '_').replace('-', '_')
                allowed = dict(s._fields['networks'].selection).keys()
                if key in allowed:
                    s.networks = key

    # ------------------------------------------------------------------
    # Cancel / Uncancel actions  (Deal Revisions LTC tab — Phase 1 part)
    # ------------------------------------------------------------------
    def action_cancel_schedule(self):
        for s in self:
            s.status = 'canceled'
        return True

    def action_uncancel_schedule(self):
        for s in self:
            s.status = 'sold'
        return True
