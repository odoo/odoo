from odoo import api, fields, models


class KswDeductionLine(models.Model):
    _name = 'ksw.deduction.line'
    _description = 'KSW Deduction Installment Line'
    _order = 'deduction_id, sequence, year, month'

    deduction_id = fields.Many2one(
        'ksw.deduction', required=True, ondelete='cascade',
        string='Deduction',
    )
    sequence = fields.Integer(string='#', default=1)
    year = fields.Integer(required=True)
    month = fields.Integer(required=True, help='Month number (1-12)')
    period_date = fields.Date(
        compute='_compute_period_date', store=True,
        help='First day of (year, month) — used for payslip period matching.',
    )
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(
        related='deduction_id.currency_id', store=True, readonly=True,
    )
    state = fields.Selection([
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('skipped', 'Skipped'),
    ], default='pending', required=True, copy=False)
    payslip_id = fields.Many2one(
        'hr.payslip', readonly=True, copy=False,
        help='Payslip that consumed this installment.',
    )
    # Display helpers
    employee_id = fields.Many2one(
        related='deduction_id.employee_id', store=True, readonly=True,
    )
    type_id = fields.Many2one(
        related='deduction_id.type_id', store=True, readonly=True,
    )

    _valid_month = models.Constraint(
        'CHECK(month >= 1 AND month <= 12)',
        'Month must be between 1 and 12.',
    )

    @api.depends('year', 'month')
    def _compute_period_date(self):
        for line in self:
            if line.year and line.month:
                line.period_date = fields.Date.to_date(
                    '%04d-%02d-01' % (line.year, line.month))
            else:
                line.period_date = False

    def name_get(self):
        res = []
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        for line in self:
            label = '%s %d' % (
                month_names[line.month] if 1 <= line.month <= 12 else '?',
                line.year or 0,
            )
            res.append((line.id, label))
        return res

