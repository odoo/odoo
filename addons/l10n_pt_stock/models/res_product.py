from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, values):
        if not values.get('name'):
            return super().write(values)
        pt_product_templates = self.filtered(lambda pt: not pt.company_id or pt.company_id.account_fiscal_country_id.code == 'PT')
        if pt_product_templates:
            stock_moves_with_product = self.env['stock.move'].search([
                ('product_id.product_tmpl_id', 'in', pt_product_templates.ids),
                ('picking_id.state', '=', 'done'),
                ('product_id.product_tmpl_id.name', '!=', False),
            ]).filtered(lambda p: p.country_code == 'PT')
            if stock_moves_with_product:
                raise UserError(_("You cannot modify the name of a product that has been used in a transfer in Portugal."))
        return super().write(values)
