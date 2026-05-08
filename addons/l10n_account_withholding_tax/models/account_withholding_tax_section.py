from odoo import fields, models


class AccountWithholdingTaxSection(models.Model):
    _name = 'account.withholding.tax.section'
    _description = "Withholding Tax Section"
    _check_company_auto = True

    name = fields.Char("Section Name")
    consider_amount = fields.Selection([
            ('untaxed_amount', 'Untaxed Amount'),
            ('total_amount', 'Total Amount'),
        ], string="Consider", default='untaxed_amount', required=True)
    is_per_transaction_limit = fields.Boolean("Per Transaction")
    per_transaction_limit = fields.Float("Per Transaction limit")
    is_aggregate_limit = fields.Boolean("Aggregate")
    aggregate_limit = fields.Float("Aggregate limit")
    aggregate_period = fields.Selection([
            ('monthly', 'Monthly'),
            ('fiscal_yearly', 'Financial Yearly'),
        ], string="Aggregate Period", default='fiscal_yearly')
    tax_ids = fields.One2many("account.tax", "withholding_tax_section_id", string="Taxes")
    withholding_sequence_id = fields.Many2one(
        string='Withholding Sequence',
        help='This sequence will be used to generate default numbers on payment withholding lines.',
        comodel_name='ir.sequence',
        copy=False,
        check_company=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )

    _per_transaction_limit = models.Constraint(
        'CHECK(per_transaction_limit >= 0)',
        'Per transaction limit must be positive',
    )
    _aggregate_limit = models.Constraint(
        'CHECK(aggregate_limit >= 0)',
        'Aggregate limit must be positive',
    )
