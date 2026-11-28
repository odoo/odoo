# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import _, api, models
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def write(self, vals):
        if not vals.get('active', True) or ('phantom' in self.mapped('type') and vals.get('type', 'phantom') != 'phantom'):
            self._ensure_bom_is_free()
        return super().write(vals)

    @api.ondelete(at_uninstall=True)
    def _ensure_bom_is_free(self):
        product_ids = []
        product_bom_company = defaultdict(set)
        for bom in self:
            if not bom.active or bom.type != 'phantom':
                continue
            # Accumulate the products of this bom for the "is it delivered"
            # search, but only map THIS bom's company to THIS bom's products.
            # Mapping against the accumulated product_ids would wrongly attribute
            # every earlier product to this bom's company, blocking the archive
            # of BOMs belonging to other companies (see issue #297830).
            bom_product_ids = bom.product_id.ids or bom.product_tmpl_id.product_variant_ids.ids
            product_ids += bom_product_ids
            for product_id in bom_product_ids:
                product_bom_company[product_id].add(bom.company_id.id)
        if not product_ids:
            return
        related_lines = self.env['sale.order.line'].sudo().search([
            ('state', '=', 'sale'),
            ('invoice_status', 'in', ('no', 'to invoice')),
            ('product_id', 'in', product_ids),
            ('move_ids.state', '!=', 'cancel'),
        ])
        problematic_line_ids = set()
        for sol in related_lines:
            company_ids = product_bom_company[sol.product_id.id]
            if False in company_ids or sol.company_id.id in company_ids:
                problematic_line_ids.add(sol.id)
        lines = self.env['sale.order.line'].browse(problematic_line_ids)
        if lines:
            product_names = ', '.join(lines.product_id.mapped('display_name'))
            raise UserError(_('As long as there are some sale order lines that must be delivered/invoiced and are '
                              'related to these bills of materials, you can not remove them.\n'
                              'The error concerns these products: %s', product_names))
