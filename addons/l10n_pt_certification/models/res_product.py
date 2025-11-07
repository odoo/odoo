from odoo import _, api, models
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
        if len(values['name']) < 2:
            raise UserError(_("Product names have to be at least 2 characters long."))
        if (
                (pt_product_templates := self.filtered(lambda pt: not pt.company_id or pt.company_id.account_fiscal_country_id.code == 'PT'))
                and self.env['account.move.line'].search_count([
                    ('product_id.product_tmpl_id', 'in', pt_product_templates.ids),
                    ('parent_state', '=', 'posted'),
                    ('product_id.product_tmpl_id.name', '!=', False),
                    ('move_id.country_code', '=', 'PT'),
                ], limit=1)
        ):
            raise UserError(_("You cannot modify the name of a product that has been used in an accounting entry."))
        return super().write(values)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model_create_multi
    def create(self, values):
        res = super().create(values)
        for product in res:
            # Products should have a unique default code for Portugal.
            if 'PT' in product.fiscal_country_codes and not product.default_code:
                product.default_code = f"{product.name.replace(' ', '_').upper()[:4]}_{product.id}"
        return res
