# Part of TNPD Prison HR Employee Extension.
# License: LGPL-3

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class TransferApprovalRequest(models.Model):
    _name = 'transfer.approval.request'
    _description = 'Transfer Approval Request'
    _rec_name = 'employee_id'
    _order = 'create_date desc'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Employee',
        required=True,
        ondelete='restrict',
        index=True,
    )

    # Snapshot of the employee's current posting at request time (read-only)
    current_central_prison = fields.Many2one(
        comodel_name='tnpd.prison.master',
        string='Current Central Prison',
        domain=[('prison_type', '=', 'central')],
        readonly=True,
    )
    current_district_jail = fields.Many2one(
        comodel_name='tnpd.prison.master',
        string='Current District Jail',
        domain=[('prison_type', '=', 'district')],
        readonly=True,
    )
    current_sub_jail = fields.Many2one(
        comodel_name='tnpd.prison.master',
        string='Current Sub Jail',
        domain=[('prison_type', '=', 'sub')],
        readonly=True,
    )

    # Requested transfer destination
    requested_central_prison = fields.Many2one(
        comodel_name='tnpd.prison.master',
        string='Requested Central Prison',
        domain=[('prison_type', '=', 'central')],
        required=True,
    )
    requested_district_jail = fields.Many2one(
        comodel_name='tnpd.prison.master',
        string='Requested District Jail',
        domain=[('prison_type', '=', 'district')],
        required=True,
    )
    requested_sub_jail = fields.Many2one(
        comodel_name='tnpd.prison.master',
        string='Requested Sub Jail',
        domain=[('prison_type', '=', 'sub')],
        required=True,
    )

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @api.model
    def _lookup_prison(self, prison_type, name):
        """Return the tnpd.prison.master id matching *name* and *prison_type*, or False."""
        if not name:
            return False
        record = self.env['tnpd.prison.master'].search(
            [('name', '=', name), ('prison_type', '=', prison_type)],
            limit=1,
        )
        return record.id if record else False

    @api.model
    def _current_prison_vals_from_employee(self, employee):
        """
        Build a dict of current_* prison field values sourced from the
        employee's Char fields.  Resolves each value against prison.master;
        unmatched values are left as False (no record found).
        """
        return {
            'current_central_prison': self._lookup_prison(
                'central', employee.x_central_prison
            ),
            'current_district_jail': self._lookup_prison(
                'district', employee.x_district_jail
            ),
            'current_sub_jail': self._lookup_prison(
                'sub', employee.x_sub_jail
            ),
        }
