# -*- coding: utf-8 -*-
"""Phase 1 — Advertiser Finance-hold logic on top of the auto-generated mv.advertiser.

The deal-creation flow (Workflow 1 step 3) requires checking three Finance signals
on the Advertiser:
  * `hold_placed_on_advertiser_account` (manual flag from Finance)
  * `advertiser_approved_to_book` == False  (Finance approval missing)
  * `adv_log_with_expiration_date` is in the past  (LOG expired)

This module composes those into a single computed `finance_hold` boolean that
Deal validations look at.  Cron-based LOG expiration alerts live in Phase 3.
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class MvAdvertiserPhase1(models.Model):
    _inherit = 'mv.advertiser'

    finance_hold = fields.Boolean(
        string='Finance Hold',
        compute='_compute_finance_hold',
        store=True,
        help='Aggregates manual hold flag, approved-to-book flag, '
             'and LOG expiration. When True, Deal creation is blocked.',
    )
    finance_hold_reason = fields.Char(
        string='Finance Hold Reason',
        compute='_compute_finance_hold',
        store=True,
    )

    @api.depends(
        'hold_placed_on_advertiser_account',
        'advertiser_approved_to_book',
        'advertiser_cia',
        'adv_log_with_expiration_date',
    )
    def _compute_finance_hold(self):
        today = fields.Date.context_today(self)
        for a in self:
            reasons = []
            if a.hold_placed_on_advertiser_account:
                reasons.append(_("manual hold by Finance"))
            if not a.advertiser_approved_to_book:
                reasons.append(_("not approved to book by Finance"))
            if a.adv_log_with_expiration_date and a.adv_log_with_expiration_date < today:
                reasons.append(_("LOG expired (%s)") % a.adv_log_with_expiration_date)
            if a.advertiser_cia:
                reasons.append(_("CIA — needs payment confirmation"))
            a.finance_hold = bool(reasons)
            a.finance_hold_reason = '; '.join(reasons) if reasons else ''
