from odoo import api, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model_create_multi
    def create(self, values):
        for value in values:
            if len(value.get('name', 0)) < 2:
                raise UserError(_("Product names have to be at least 2 characters long."))
        return super().create(values)

    def write(self, values):
        if not values.get('name'):
            return super().write(values)
        for product_template in self:
            if (
                (not product_template.company_id or product_template.company_id.account_fiscal_country_id.code == 'PT')
                and product_template.name
                and self.env['account.move.line'].search_count([
                    ('product_id.product_tmpl_id', '=', product_template.id),
                    ('parent_state', '=', 'posted'),
                ])
            ):
                raise UserError(_("You cannot modify the name of a product that has been used in an accounting entry."))
            if len(values['name']) < 2:
                raise UserError(_("Product names have to be at least 2 characters long."))
        return super().write(values)
