# -*- coding: utf-8 -*-
"""Phase 3 — SF Credit Memo (SFCM) workflow (SF Workflow 17).

The auto-generated mv.sf_credit_memo already has a SF-style `status` Selection
field. This layer adds:
  * Approval routing per the SF amount-based matrix:
      - Credit type, < $1k       → Arunna (placeholder)
      - Credit type, ≥ $1k       → Jake (placeholder)
      - Network Error            → Charles (placeholder)
      - Agency Discount          → Charles + Jake
  * action_submit_for_approval / action_approve / action_reject buttons.
  * Locks the record after approval (state='approved' makes most fields readonly).
  * 'amount' computed from SFCM details total when present.

Group routing is left as a TODO placeholder until the Finance/Ops groups are
wired up in Phase 3.5.
"""
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class MvSfCreditMemoPhase3(models.Model):
    _inherit = 'mv.sf_credit_memo'

    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    approval_state = fields.Selection(
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

    # Amount fields — convenience for routing logic
    sfcm_amount = fields.Monetary(
        string='SFCM Amount',
        compute='_compute_sfcm_amount',
        store=True,
        currency_field='currency_id',
        help='Sum of all SF Credit Memo Details for this memo.',
    )

    @api.depends('sf_external_id')  # TODO: refine when SFCM Detail O2m is wired
    def _compute_sfcm_amount(self):
        Detail = self.env.get('mv.sf_credit_memo_detail')
        for memo in self:
            if Detail is None:
                memo.sfcm_amount = 0.0
                continue
            details = Detail.search([('sf_credit_memo', '=', memo.id)]) if 'sf_credit_memo' in Detail._fields else Detail.browse()
            # Look for any field on the detail that contains "gross" or "total" or "amount"
            total = 0.0
            for d in details:
                for fname in ('amount','gross','gross_amount','total','net_amount'):
                    if fname in d._fields and d[fname]:
                        try:
                            total += float(d[fname])
                            break
                        except Exception:
                            pass
            memo.sfcm_amount = total

    def _required_approver_note(self):
        self.ensure_one()
        type_ = self.type or 'credit'
        amount = self.sfcm_amount or 0.0
        if type_ == 'credit':
            return _('Approver: %s (Credit type, $%s)') % ('Arunna' if amount < 1000 else 'Jake', amount)
        if type_ == 'network_error':
            return _('Approver: Charles (Network Error)')
        if type_ in ('agency_discount', 'agency_discount_approved_by_network'):
            return _('Approvers: Charles + Jake (Agency Discount)')
        if type_ in ('bundles_credit', 'bundles_performance', 'network_performance'):
            return _('Approver: Jake (Bundles)')
        return _('Approver: TBD')

    def action_submit_for_approval(self):
        for memo in self:
            if memo.approval_state not in ('draft', 'rejected'):
                raise UserError(_("SFCM %s is already %s.") % (memo.display_name, memo.approval_state))
            if not memo.type:
                raise UserError(_("Please set the SFCM Type before submitting (Credit / Network Error / Agency Discount / etc.)."))
            memo.approval_state = 'submitted'
            memo.submitted_by_id = self.env.user.id
            memo.submitted_date = fields.Datetime.now()
            memo.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=_('Approve SFCM: %s') % (memo.display_name or ''),
                note=memo._required_approver_note(),
                user_id=self.env.user.id,  # TODO: route to the named approver group
            )
            memo.message_post(body=_("SFCM submitted for approval. %s") % memo._required_approver_note())
        return True

    def action_approve(self):
        for memo in self:
            if memo.approval_state != 'submitted':
                raise UserError(_("Only Submitted SFCMs can be approved (current: %s).") % memo.approval_state)
            memo.approval_state = 'approved'
            memo.approved_by_id = self.env.user.id
            memo.approved_date = fields.Datetime.now()
            memo.message_post(body=_("SFCM approved by %s.") % self.env.user.display_name)
        return True

    def action_reject(self):
        for memo in self:
            if memo.approval_state != 'submitted':
                raise UserError(_("Only Submitted SFCMs can be rejected (current: %s).") % memo.approval_state)
            memo.approval_state = 'rejected'
            memo.message_post(body=_("SFCM rejected by %s. Reason: %s")
                              % (self.env.user.display_name, memo.rejection_reason or '—'))
        return True
