# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockPackageHistory(models.Model):
    _name = 'stock.package.history'
    _description = "Stock Package History"
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    location_id = fields.Many2one('stock.location', 'Origin Location')
    location_dest_id = fields.Many2one('stock.location', 'Destination Location')
    move_line_ids = fields.Many2many('stock.move.line', string='Move Lines', required=True)
    package_id = fields.Many2one('stock.package', 'Package', required=True)
    package_name = fields.Char('Package Name', required=True)
    package_type_id = fields.Many2one('stock.package.type', related='package_id.package_type_id')
    parent_orig_id = fields.Many2one('stock.package', 'Origin Container')
    parent_dest_id = fields.Many2one('stock.package', 'Destination Container')
    picking_ids = fields.Many2many('stock.picking', string='Transfers', compute='_compute_picking_ids', search="_search_picking_ids")

    @api.depends('move_line_ids.picking_id')
    def _compute_picking_ids(self):
        for history in self:
            history.picking_ids = history.move_line_ids.picking_id

    def _search_picking_ids(self, operator, value):
        return [('move_line_ids.picking_id', operator, value)]
