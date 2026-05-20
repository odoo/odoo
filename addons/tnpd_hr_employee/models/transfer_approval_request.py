# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import logging

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
        pending  →  approved  (updates employee jail posting)
        pending  →  rejected
    """

    _name = 'transfer.approval.request'
    _description = 'Transfer Approval Request'
    _rec_name = 'employee_id'
    _order = 'create_date desc'

    # ── Employee ──────────────────────────────────────────────────────────────

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
    )

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

    # ── Workflow ──────────────────────────────────────────────────────────────

    approval_user_id = fields.Many2one(
        comodel_name='res.users',
        string='Approval User',
        required=True,
        index=True,
    )
    state = fields.Selection(
        selection=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        string='State',
        default='pending',
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

    # ── Actions: Approve / Reject ─────────────────────────────────────────

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
