from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = "product.product"

    expense_job_position_limit_ids = fields.One2many(
        comodel_name='hr.expense.product.job.position.limit',
        inverse_name='product_id',
        string="Job Position Limits",
        copy=True,
    )

    def get_standard_price_update_warning(self, new_standard_price):
        self.ensure_one()
        undone_expenses = self.env['hr.expense']._read_group(
            domain=[('state', '=', 'draft'), ('product_id', '=', self.id)],
            groupby=['price_unit'],
            )
        # The following list is composed of all the price_units of expenses that use this product and should NOT trigger a warning.
        # Those are the amounts of any undone expense using this product and 0.0 which is the default unit_amount.
        unit_amounts_no_warning = [self.env.company.currency_id.round(row[0]) for row in undone_expenses]

        if undone_expenses:
            rounded_price = self.env.company.currency_id.round(new_standard_price)
            if (len(unit_amounts_no_warning) > 1 or (len(unit_amounts_no_warning) == 1 and rounded_price not in unit_amounts_no_warning)):
                return self.env._(
                    "There are draft expenses linked to this product. Updating the product cost will change expense amounts. "
                    "Make sure it is what you want to do.",
                )
        return False

    def write(self, vals):
        result = super().write(vals)
        if 'standard_price' in vals:
            expenses_sudo = self.env['hr.expense'].sudo().search([
                ('company_id', '=', self.env.company.id),
                ('product_id', 'in', self.ids),
                ('state', '=', 'draft'),
            ])
            for expense_sudo in expenses_sudo:
                expense_product_sudo = expense_sudo.product_id
                product_has_cost = (
                        expense_product_sudo
                        and not expense_sudo.company_currency_id.is_zero(expense_product_sudo.standard_price)
                )
                expense_vals = {
                    'product_has_cost': product_has_cost,
                }
                if product_has_cost:
                    expense_vals.update({
                        'price_unit': expense_product_sudo.standard_price,
                    })
                else:
                    expense_vals.update({
                        'quantity': 1,
                        'price_unit': expense_sudo.total_amount
                    })
                expense_sudo.write(expense_vals)
        return result


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
    currency_id = fields.Many2one(
        related='product_id.currency_id',
        readonly=True,
    )
    limit_amount = fields.Monetary(
        string="Limit",
        currency_field='currency_id',
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
