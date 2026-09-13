from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrExpenseProductJobPositionLimit(models.Model):
    _name = 'hr.expense.product.job.position.limit'
    _description = "Expense Product Limit by Job Position"
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    product_id = fields.Many2one(
        comodel_name='product.product',
        required=True,
        ondelete='cascade',
        index=True,
    )
    job_ids = fields.Many2many(
        comodel_name='hr.job',
        string="Job Positions",
        help="Leave empty to define the limit for all job positions.",
    )
    company_currency_id = fields.Many2one(
        related='product_id.cost_currency_id',
    )
    limit_amount = fields.Monetary(
        string="Limit",
        currency_field='company_currency_id',
        required=True,
    )

    @api.constrains('product_id', 'job_ids')
    def _check_unique_generic_job_position_limit(self):
        for limit in self.filtered(lambda line: not line.job_ids):
            duplicate = self.search_count([
                ('product_id', '=', limit.product_id.id),
                ('job_ids', '=', False),
                ('id', '!=', limit.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(self.env._("Only one generic expense limit can be defined per product."))
