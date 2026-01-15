# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPackageHistory(models.Model):
    _name = 'stock.package.history'
    _description = "Stock Package History"
    _check_company_auto = True

    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    location_id = fields.Many2one('stock.location', 'Origin Location')
    location_dest_id = fields.Many2one('stock.location', 'Destination Location')
    move_line_ids = fields.One2many('stock.move.line', 'package_history_id', string='Move Lines', required=True)
    package_id = fields.Many2one('stock.package', 'Package', required=True, ondelete='cascade')
    package_name = fields.Char('Package Name', required=True)
    package_type_id = fields.Many2one('stock.package.type', related='package_id.package_type_id')
    parent_orig_id = fields.Many2one('stock.package', 'Origin Container')
    parent_orig_name = fields.Char('Origin Container Name')
    parent_dest_id = fields.Many2one('stock.package', 'Destination Container')
    parent_dest_name = fields.Char('Destination Container Name')
    outermost_dest_id = fields.Many2one('stock.package', 'Outermost Destination Container')
    picking_ids = fields.Many2many('stock.picking', string='Transfers')

    def _get_complete_dest_name_except_outermost(self):
        self.ensure_one()
        if not self.parent_dest_id:
            return ''
        elif self.parent_dest_id == self.outermost_dest_id:
            return self.package_id.name

        # Complete name without the first (outermost) package name
        return ' > '.join(self.package_name.split(' > ')[1:])
