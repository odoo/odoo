# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    use_expiration_date = fields.Boolean(related='product_id.use_expiration_date')

    def _read_qties(self, date, wh):
        res = super()._read_qties(date, wh)
        if any(self.mapped('use_expiration_date')):
            i = 0
            for record in self.mapped('product_id').with_context(warehouse_id=wh).read(['free_qty']):
                res[i]['free_qty'] = record['free_qty']
                i += 1
        return res
