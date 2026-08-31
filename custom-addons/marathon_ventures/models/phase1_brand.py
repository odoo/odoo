# -*- coding: utf-8 -*-
"""Phase 1 — Brand approval workflow on top of the auto-generated mv.brands.

What this layer adds:
  * action_submit_for_approval / action_approve / action_reject buttons.
  * Default approval_status = 'pending' on create.
  * mail.activity routed to Analytics group (placeholder — defaults to creator until
    the Analytics group is wired up in Phase 3).
  * One2many to mv.deal (so Brand → Deals related list works).
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MvBrandsPhase1(models.Model):
    _inherit = 'mv.brands'

    # ------------------------------------------------------------------
    # Related deals (Brand → Deals related list)
    # ------------------------------------------------------------------
    deal_ids = fields.One2many(
        comodel_name='mv.deal',
        inverse_name='brands',
        string='Deals',
    )
    deal_count = fields.Integer(
        string='# Deals',
        compute='_compute_deal_count',
    )

    @api.depends('deal_ids')
    def _compute_deal_count(self):
        for b in self:
            b.deal_count = len(b.deal_ids)

    # ------------------------------------------------------------------
    # Default state on create
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'approval_status' not in vals or not vals.get('approval_status'):
                vals['approval_status'] = 'pending'
        return super().create(vals_list)

    # ------------------------------------------------------------------
    # Approval state machine
    # ------------------------------------------------------------------
    def action_submit_for_approval(self):
        for b in self:
            if b.approval_status not in ('pending', False, None):
                raise UserError(_(
                    "Brand %s is already %s; nothing to submit."
                ) % (b.display_name, b.approval_status))
            b.approval_status = 'pending'
            # Schedule an activity for the creator — Analytics group routing TODO Phase 3
            b.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Approve Brand: %s') % (b.display_name or ''),
                note=_('Submitted for Brand Approval by %s. Verify Advertiser association and Category.') % b.create_uid.display_name,
                user_id=b.create_uid.id,
            )
        return True

    def action_approve(self):
        for b in self:
            b.approval_status = 'approved'
            b.approved_duplicate = 'approved'
        return True

    def action_reject(self):
        for b in self:
            b.approval_status = 'rejected'
            b.approved_duplicate = 'not_approved'
        return True

    def action_open_deals(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deals — %s') % (self.display_name or ''),
            'res_model': 'mv.deal',
            'view_mode': 'list,form',
            'domain': [('brands', '=', self.id)],
        }
