# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import get_timedelta


class StockLot(models.Model):
    _inherit = 'stock.lot'

    warranty_end_date = fields.Date(
        compute='_compute_warranty_end_date', store=True, readonly=False,
        help="This is the end date of the warranty for this tracked product.")
    warranty_id = fields.Many2one('product.warranty', compute='_compute_warranty_id', store=True, readonly=False)

    @api.depends('location_id')
    def _compute_warranty_end_date(self):
        to_compute = self.filtered(lambda lot: not lot.warranty_end_date and lot.warranty_id)
        delivery_ids_by_lot = to_compute._find_delivery_ids_by_lot()
        for lot in to_compute:
            if len(delivery_ids_by_lot[lot.id]) > 0:
                last_delivery = self.env['stock.picking'].browse(delivery_ids_by_lot[lot.id]).sorted(key='date_done', reverse=True)[0]
                lot.warranty_end_date = last_delivery.date_done + get_timedelta(lot.warranty_id.duration, lot.warranty_id.duration_unit)

    def _compute_warranty_id(self):
        for lot in self:
            lot.warranty_id = lot.product_id.default_warranty_id
