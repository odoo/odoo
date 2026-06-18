from odoo import fields, models


class KswDeductionType(models.Model):
    _name = 'ksw.deduction.type'
    _description = 'KSW Deduction Type'
    _order = 'sequence, name'

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        help='Short unique code used on payslip input lines (e.g. LOAN, GOVPEN).',
    )
    category = fields.Selection([
        ('borrowed', 'Borrowed (with employee consent)'),
        ('company_paid', 'Company Paid (on behalf of employee)'),
    ], required=True, default='borrowed',
        help='Borrowed: employee receives money (loan, advance). '
             'Company-paid: company settles a cost on behalf of the employee '
             '(gov/internal penalty).',
    )
    is_loan = fields.Boolean(
        string='Loan (5-step Approval)',
        default=False,
        help='When enabled, this type triggers the full DM -> HR -> Accounting '
             '-> GM approval workflow. Otherwise the deduction is activated '
             'instantly on creation.',
    )
    default_installments = fields.Integer(
        default=1,
        help='Suggested number of installments when creating a new deduction '
             'of this type. Can be overridden per record.',
    )
    description = fields.Text()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _unique_code = models.Constraint(
        'UNIQUE(code)',
        'The deduction type code must be unique.',
    )
    _positive_installments = models.Constraint(
        'CHECK(default_installments >= 1)',
        'Default installments must be at least 1.',
    )

