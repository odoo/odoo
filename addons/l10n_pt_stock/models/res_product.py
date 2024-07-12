from odoo import _, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, values):
        if not values.get('name'):
            return super().write(values)
        pt_product_templates = self.filtered(lambda pt: not pt.company_id or pt.company_id.account_fiscal_country_id.code == 'PT')
        # Only issued transport documents count, cancelled ones included; receipts and internal steps
        # are not documents (Despacho 8632/2014 3.3.5).
        if pt_product_templates and self.env['stock.move'].sudo().search_count([
            ('product_id.product_tmpl_id', 'in', pt_product_templates.ids),
            ('picking_id.l10n_pt_document_number', '!=', False),
        ], limit=1):
            raise UserError(_("You cannot modify the name of a product that has been used in a transfer in Portugal."))
        return super().write(values)
