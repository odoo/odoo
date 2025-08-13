from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, values):
        if not values.get('name'):
            return super().write(values)
        pt_product_templates = self.filtered(lambda pt: not pt.company_id or pt.company_id.account_fiscal_country_id.code == 'PT')
        if pt_product_templates:
            sol_with_product = self.env['sale.order.line'].search([
                ('product_id.product_tmpl_id', 'in', pt_product_templates.ids),
                ('order_id.l10n_pt_sale_inalterable_hash', '!=', False),
                ('product_id.product_tmpl_id.name', '!=', False),
                ('order_id.country_code', '=', 'PT'),
            ])
            if sol_with_product:
                raise UserError(_("You cannot modify the name of a product that has been used in a quotation or sales order."))
        return super().write(values)
