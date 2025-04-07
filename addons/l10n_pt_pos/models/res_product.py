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
                and product_template.name != values['name']
                and self.env['pos.order.line'].search_count([
                    ('product_id.product_tmpl_id', '=', product_template.id),
                    ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
                ])
            ):
                raise UserError(_("You cannot modify the name of a product that has been used in an POS order."))
        return super().write(values)
