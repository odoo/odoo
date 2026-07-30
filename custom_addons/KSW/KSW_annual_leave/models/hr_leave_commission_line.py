from odoo import fields, models


class HrLeaveCommissionLine(models.Model):
    _name = 'hr.leave.commission.line'
    _description = 'Leave Commission Line'
    _order = 'sequence, id'

    leave_id = fields.Many2one(
        'hr.leave', string='Leave', required=True, ondelete='cascade',
        index=True,
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Month / Description', required=True,
        help='E.g. "January 2026", "Feb 2026 bonus", etc.',
    )
    amount = fields.Float(
        string='Amount', digits=(16, 2), required=True,
    )

