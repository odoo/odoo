from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, values):
        if not values.get('name'):
            return super().write(values)
        pt_product_templates = self.filtered(lambda pt: not pt.company_id or pt.company_id.account_fiscal_country_id.code == 'PT')
        if pt_product_templates and self.env['pos.order.line'].search([
            ('product_id.product_tmpl_id', 'in', pt_product_templates.ids),
            ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ('order_id.country_code', '=', 'PT'),
        ]):
            raise UserError(_("You cannot modify the name of a product that has been used in a POS order in Portugal."))
        return super().write(values)
