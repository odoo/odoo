from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    standard_price_update_warning = fields.Char(compute="_compute_standard_price_update_warning")

    @api.onchange('standard_price')
    def _compute_standard_price_update_warning(self):
        undone_expenses = self.env['hr.expense']._read_group(
            domain=[('state', 'in', ['draft', 'reported']), ('product_id', 'in', self.ids)],
            groupby=['price_unit'],
            )
        # The following list is composed of all the unit_amounts of expenses that use this product and should NOT trigger a warning.
        # Those are the amounts of any undone expense using this product and 0.0 which is the default unit_amount.
        unit_amounts_no_warning = [self.env.company.currency_id.round(row[0]) for row in undone_expenses]
        for product in self:
            product.standard_price_update_warning = False
            if undone_expenses:
                rounded_price = self.env.company.currency_id.round(product.standard_price)
                if rounded_price and (len(unit_amounts_no_warning) > 1 or (len(unit_amounts_no_warning) == 1 and rounded_price not in unit_amounts_no_warning)):
                    product.standard_price_update_warning = _(
                            "There are unsubmitted expenses linked to this category. Updating the category cost will change expense amounts. "
                            "Make sure it is what you want to do."
                        )
