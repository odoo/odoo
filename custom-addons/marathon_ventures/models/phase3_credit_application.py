# -*- coding: utf-8 -*-
"""Phase 3 — Credit Application approval workflow (SF Workflow 16).

Adds an explicit approval state machine on top of the auto-generated mv.credit_application:
  draft  → submitted  → approved | rejected

Submit-for-Approval routes a mail.activity to the Finance group placeholder;
Approve / Reject set the state, stamp the user, and notify the AE via the standard
mail.thread channel.
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MvCreditApplicationPhase3(models.Model):
    _inherit = 'mv.credit_application'

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='Approval State',
        default='draft',
        copy=False,
    )
    submitted_by_id = fields.Many2one('res.users', string='Submitted By', readonly=True, copy=False)
    submitted_date = fields.Datetime(string='Submitted On', readonly=True, copy=False)
    approved_by_id = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved On', readonly=True, copy=False)
    rejection_reason = fields.Text(string='Rejection Reason', copy=False)

    def action_submit_for_approval(self):
        for app in self:
            if app.state not in ('draft', 'rejected'):
                raise UserError(_("Credit Application is already %s.") % app.state)
            app.state = 'submitted'
            app.submitted_by_id = self.env.user.id
            app.submitted_date = fields.Datetime.now()
            app.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Review Credit Application: %s') % (app.display_name or ''),
                note=_('Application submitted by %s. Review DB Risk, CS Risk/Score, references and recommend credit limit + terms.') % self.env.user.display_name,
                user_id=self.env.user.id,  # TODO: route to Finance/Controller group when groups are wired
            )
            app.message_post(body=_("Credit Application submitted for approval."))
        return True

    def action_approve(self):
        for app in self:
            if app.state != 'submitted':
                raise UserError(_("Only Submitted applications can be approved (current: %s).") % app.state)
            app.state = 'approved'
            app.approved_by_id = self.env.user.id
            app.approved_date = fields.Datetime.now()
            app.message_post(body=_("Credit Application approved by %s.") % self.env.user.display_name)
        return True

    def action_reject(self):
        for app in self:
            if app.state != 'submitted':
                raise UserError(_("Only Submitted applications can be rejected (current: %s).") % app.state)
            app.state = 'rejected'
            app.message_post(body=_("Credit Application rejected by %s. Reason: %s")
                             % (self.env.user.display_name, app.rejection_reason or '—'))
        return True

    def action_reset_to_draft(self):
        for app in self:
            if app.state == 'approved':
                raise UserError(_("Approved applications cannot be reset to draft."))
            app.state = 'draft'
            app.message_post(body=_("Credit Application reset to draft."))
        return True
