from odoo import models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, values):
        if not values.get('name'):
            return super().write(values)
        for product_template in self:
            if (
                (not product_template.company_id or product_template.company_id.account_fiscal_country_id.code == 'PT')
                and product_template.name
                and self.env['stock.move'].search_count([
                    ('product_id.product_tmpl_id', '=', product_template.id),
                    ('picking_id.state', '=', 'done'),
                ])
            ):
                raise UserError(_("You cannot modify the name of a product that has been used in a stock picking."))
        return super().write(values)
