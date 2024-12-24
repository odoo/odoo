# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')

    # NB: unused and dropped in 18.1
    def _get_warehouse_available(self):
        return (
            self.warehouse_id.id or
            self.env['ir.default'].sudo()._get('sale.order', 'warehouse_id', company_id=self.company_id.id) or
            self.env['ir.default'].sudo()._get('sale.order', 'warehouse_id') or
            self.env['stock.warehouse'].sudo().search([('company_id', '=', self.company_id.id)], limit=1).id
        )

    def _get_product_available_qty(self, product, **kwargs):
        return product.with_context(warehouse_id=self.warehouse_id.id).free_qty
