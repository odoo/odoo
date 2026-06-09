# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import logging
from datetime import date

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TransferApprovalRequest(models.Model):
    """
    Transfer Approval Request workflow model.

    Jail selection follows a strict three-tier cascade:
        Central Jail  →  District Jail  →  Sub Jail

    Onchange methods reset dependent fields when a parent changes; the
    ``_check_requested_jail_hierarchy`` constraint enforces the same rules
    at save time (covers API / batch writes that bypass onchange).

    State machine:
        draft     →  pending   (action_submit)
        pending   →  approved  (action_approve — updates employee jail posting)
        pending   →  rejected  (action_reject)
        pending   →  returned  (action_return — returned for correction)
        draft     →  cancelled (action_cancel)
        pending   →  cancelled (action_cancel)
    """

    _name = 'transfer.approval.request'
    _description = 'Transfer Approval Request'
    _rec_name = 'employee_id'
    _order = 'create_date desc'

    # ── Transfer classification ───────────────────────────────────────────────

    transfer_type = fields.Selection(
        selection=[
            ('request', 'Transfer Request'),
            ('tenure', 'Tenure Transfer'),
            ('admin_grounds', 'Administrative Grounds'),
        ],
        string='Transfer Type',
        required=True,
        default='request',
        index=True,
    )

    transfer_reason = fields.Text(
        string='Transfer Reason',
        help='Reason provided by the employee for requesting the transfer.',
    )

    priority = fields.Selection(
        selection=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
        ],
        string='Priority',
        default='medium',
        required=False,
    )

    # ── Employee ──────────────────────────────────────────────────────────────

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
    )

    # ── Computed: tenure at current station ───────────────────────────────────

    tenure_years = fields.Float(
        string='Tenure at Current Station (Years)',
        compute='_compute_tenure_years',
        store=True,
        digits=(6, 2),
        help='Years since employee was posted to the current station.',
    )

    @api.depends('employee_id', 'employee_id.x_date_present_station')
    def _compute_tenure_years(self):
        today = date.today()
        for rec in self:
            posting_date = rec.employee_id.x_date_present_station if rec.employee_id else False
            if posting_date:
                rec.tenure_years = (today - posting_date).days / 365.25
            else:
                rec.tenure_years = 0.0

    # ── Current posting (read-only snapshot at request time) ──────────────────

    current_central_prison = fields.Many2one(
        comodel_name='prison.jail',
        string='Current Central Jail',
        domain=[('jail_type', '=', 'central_jail')],
        readonly=True,
    )
    current_district_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Current District Jail',
        domain=[('jail_type', '=', 'district_jail')],
        readonly=True,
    )
    current_sub_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Current Sub Jail',
        domain=[('jail_type', '=', 'sub_jail')],
        readonly=True,
    )

    # ── Requested transfer destination (cascading selection) ──────────────────

    requested_central_prison = fields.Many2one(
        comodel_name='prison.jail',
        string='Requested Central Jail',
        domain=[('jail_type', '=', 'central_jail'), ('active', '=', True)],
        required=True,
        index=True,
        ondelete='restrict',
    )
    requested_district_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Requested District Jail',
        # Optional: Central Prisons without District Jails (e.g. Vellore,
        # Tiruchirappalli) administer Sub Jails directly.
        domain=[('jail_type', '=', 'district_jail'), ('active', '=', True)],
        index=True,
        ondelete='restrict',
    )
    requested_sub_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Requested Sub Jail',
        domain=[('jail_type', '=', 'sub_jail'), ('active', '=', True)],
        required=True,
        index=True,
        ondelete='restrict',
    )

    # ── Preference 2 ─────────────────────────────────────────────────────────

    preference_2_central_prison = fields.Many2one(
        comodel_name='prison.jail',
        string='Preference 2 — Central Prison',
        domain=[('jail_type', '=', 'central_jail'), ('active', '=', True)],
        ondelete='restrict',
    )
    preference_2_district_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Preference 2 — District Jail',
        domain=[('jail_type', '=', 'district_jail'), ('active', '=', True)],
        ondelete='restrict',
    )
    preference_2_sub_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Preference 2 — Sub Jail',
        domain=[('jail_type', '=', 'sub_jail'), ('active', '=', True)],
        ondelete='restrict',
    )

    # ── Preference 3 ─────────────────────────────────────────────────────────

    preference_3_central_prison = fields.Many2one(
        comodel_name='prison.jail',
        string='Preference 3 — Central Prison',
        domain=[('jail_type', '=', 'central_jail'), ('active', '=', True)],
        ondelete='restrict',
    )
    preference_3_district_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Preference 3 — District Jail',
        domain=[('jail_type', '=', 'district_jail'), ('active', '=', True)],
        ondelete='restrict',
    )
    preference_3_sub_jail = fields.Many2one(
        comodel_name='prison.jail',
        string='Preference 3 — Sub Jail',
        domain=[('jail_type', '=', 'sub_jail'), ('active', '=', True)],
        ondelete='restrict',
    )

    # ── Workflow ──────────────────────────────────────────────────────────────

    approval_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Approval User',
        required=True,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
            ('returned', 'Returned'),
        ],
        string='State',
        default='draft',
        required=True,
        index=True,
    )
    requested_by = fields.Many2one(
        comodel_name='res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        readonly=True,
    )
    approved_by = fields.Many2one(
        comodel_name='res.users',
        string='Actioned By',
        readonly=True,
    )
    approved_date = fields.Datetime(string='Action Date', readonly=True)
    remarks = fields.Text(string='Remarks')
    active = fields.Boolean(default=True)

    # ── Onchange: cascading reset ─────────────────────────────────────────────

    @api.onchange('requested_central_prison')
    def _onchange_requested_central_prison(self):
        """Reset district and sub when central changes; update both domains."""
        self.requested_district_jail = False
        self.requested_sub_jail = False
        if self.requested_central_prison:
            return {
                'domain': {
                    'requested_district_jail': [
                        ('jail_type', '=', 'district_jail'),
                        ('parent_id', '=', self.requested_central_prison.id),
                        ('active', '=', True),
                    ],
                    # Pre-filter sub jails by central; narrows further when DJ is chosen
                    'requested_sub_jail': [
                        ('jail_type', '=', 'sub_jail'),
                        ('parent_id', '=', self.requested_central_prison.id),
                        ('active', '=', True),
                    ],
                }
            }

    @api.onchange('requested_district_jail')
    def _onchange_requested_district_jail(self):
        """Reset sub when district changes; filter sub by DJ, or by Central if no DJ."""
        self.requested_sub_jail = False
        if self.requested_district_jail:
            return {
                'domain': {
                    'requested_sub_jail': [
                        ('jail_type', '=', 'sub_jail'),
                        ('parent_id', '=', self.requested_district_jail.id),
                        ('active', '=', True),
                    ]
                }
            }
        elif self.requested_central_prison:
            # DJ cleared or not applicable — show Sub Jails directly under Central
            return {
                'domain': {
                    'requested_sub_jail': [
                        ('jail_type', '=', 'sub_jail'),
                        ('parent_id', '=', self.requested_central_prison.id),
                        ('active', '=', True),
                    ]
                }
            }

    # ── Constraints: hierarchy integrity ─────────────────────────────────────

    @api.constrains(
        'requested_central_prison',
        'requested_district_jail',
        'requested_sub_jail',
    )
    def _check_requested_jail_hierarchy(self):
        """Ensure hierarchy is consistent: DJ belongs to Central; Sub belongs to DJ or Central."""
        for rec in self:
            if rec.requested_district_jail and rec.requested_central_prison:
                if rec.requested_district_jail.parent_id != rec.requested_central_prison:
                    raise ValidationError(
                        f'District Jail "{rec.requested_district_jail.name}" does not '
                        f'belong to Central Jail "{rec.requested_central_prison.name}".\n'
                        'Select a District Jail that falls under the chosen Central Jail.'
                    )
            if rec.requested_sub_jail:
                if rec.requested_district_jail:
                    # Sub Jail must be under the selected District Jail
                    if rec.requested_sub_jail.parent_id != rec.requested_district_jail:
                        raise ValidationError(
                            f'Sub Jail "{rec.requested_sub_jail.name}" does not belong to '
                            f'District Jail "{rec.requested_district_jail.name}".\n'
                            'Select a Sub Jail that falls under the chosen District Jail.'
                        )
                elif rec.requested_central_prison:
                    # No DJ: Sub Jail must be directly under the Central Prison
                    if rec.requested_sub_jail.parent_id != rec.requested_central_prison:
                        raise ValidationError(
                            f'Sub Jail "{rec.requested_sub_jail.name}" is not directly '
                            f'under Central Jail "{rec.requested_central_prison.name}".\n'
                            'Select a Sub Jail that belongs to the chosen Central Jail.'
                        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    @api.model
    def _current_prison_vals_from_employee(self, employee):
        """
        Build current_* field values from the employee's jail Many2one fields.
        Falls back to the legacy Char-field lookup if the Many2one fields are
        not yet populated (migration period).
        """
        # Prefer the new Many2one jail fields
        if employee.x_central_jail_id or employee.x_district_jail_id or employee.x_sub_jail_id:
            return {
                'current_central_prison': employee.x_central_jail_id.id or False,
                'current_district_jail':  employee.x_district_jail_id.id or False,
                'current_sub_jail':       employee.x_sub_jail_id.id or False,
            }

        # Legacy fallback: resolve the old Char fields against prison.jail
        return {
            'current_central_prison': self._lookup_jail('central_jail', employee.x_central_prison),
            'current_district_jail':  self._lookup_jail('district_jail', employee.x_district_jail),
            'current_sub_jail':       self._lookup_jail('sub_jail', employee.x_sub_jail),
        }

    # ── Actions: Submit / Cancel / Return ────────────────────────────────────

    def action_submit(self):
        """Move draft → pending."""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError('Only draft requests can be submitted.')
        self.write({'state': 'pending'})

    def action_cancel(self):
        """Move draft/pending → cancelled."""
        self.ensure_one()
        if self.state not in ('draft', 'pending'):
            raise UserError('Only draft or pending requests can be cancelled.')
        self.write({'state': 'cancelled'})

    def action_return(self):
        """Move pending → returned (for correction). Approver only."""
        self.ensure_one()
        if self.approval_user_id != self.env.user:
            raise UserError(
                'Only the designated approver (%s) can return this request.'
                % self.approval_user_id.name
            )
        if self.state != 'pending':
            raise UserError('Only pending requests can be returned for correction.')
        self.write({'state': 'returned'})

    # ── Actions: Approve / Reject ─────────────────────────────────────────

    def _send_transfer_notification(self, notification_type, message):
        """Create a tnpd.notification record for the linked employee."""
        try:
            self.env['tnpd.notification'].sudo().create({
                'employee_id':         self.employee_id.id,
                'transfer_request_id': self.id,
                'notification_type':   notification_type,
                'action_type':         notification_type,
                'message':             message,
                'sent_by':             self.env.user.id,
            })
        except Exception:
            pass  # Never let notification failure block the approval flow

    def action_approve(self):
        self.ensure_one()
        if self.approval_user_id != self.env.user:
            raise UserError(
                'Only the designated approver (%s) can approve this request.'
                % self.approval_user_id.name
            )
        if self.state != 'pending':
            raise UserError('Only pending requests can be approved.')
        self.employee_id.write({
            'x_central_jail_id': self.requested_central_prison.id or False,
            'x_district_jail_id': self.requested_district_jail.id or False,
            'x_sub_jail_id': self.requested_sub_jail.id or False,
        })
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        to_jail = (
            self.requested_sub_jail.name
            or self.requested_district_jail.name
            or self.requested_central_prison.name
            or 'the requested posting'
        )
        self._send_transfer_notification(
            'transfer_approved',
            f'Your transfer request (Ref: TRF/{self.id}) has been approved. '
            f'You have been transferred to {to_jail}. '
            f'Approved by: {self.env.user.name}.',
        )

    def action_reject(self):
        self.ensure_one()
        if self.approval_user_id != self.env.user:
            raise UserError(
                'Only the designated approver (%s) can reject this request.'
                % self.approval_user_id.name
            )
        if self.state != 'pending':
            raise UserError('Only pending requests can be rejected.')
        self.write({
            'state': 'rejected',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
        })
        self._send_transfer_notification(
            'transfer_rejected',
            f'Your transfer request (Ref: TRF/{self.id}) has been rejected. '
            f'Please contact your administrator for more information.',
        )

    @api.model
    def _lookup_jail(self, jail_type, name):
        """
        Return the prison.jail id matching *name* and *jail_type*, or False.
        Used as a legacy bridge during the Char → Many2one migration period.
        """
        if not name:
            return False
        record = self.env['prison.jail'].search(
            [('name', '=', name), ('jail_type', '=', jail_type)],
            limit=1,
        )
        return record.id if record else False
