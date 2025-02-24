from odoo import fields, models


class HrLeaveAccrualDetail(models.Model):
    _name = 'hr.leave.accrual.detail'
    _description = "Accrual Plan Detail"

    allocation_id = fields.Many2one('hr.leave.allocation', string='Allocation', ondelete='cascade')
    date = fields.Date(string='Date', required=True)
    reason = fields.Selection([
        ('allocation_creation', 'Allocation Creation'),
        ('allocation_expiration', 'Allocation Expiration'),
        ('allocation_update', 'Allocation Manual Update'),
        ('carryover_none', 'Carry over None'),
        ('carryover_partial', 'Carry over Partial'),
        ('carryover_all', 'Carry over All'),
        ('carryover_expiration', 'Expiration of carry over'),
        ('accrual', 'Accrual'),
        ('accrual_yearly', 'Accrual (Yearly cap)'),
        ('accrual_milestone', 'Accrual (Milestone cap)'),
        ('milestone_transition', 'Milestone transition'),
    ], string='Reason', required=True)
    level_sequence = fields.Integer(string='Milestone Reached', required=True)
    added_days = fields.Float(string='Duration', required=True)
