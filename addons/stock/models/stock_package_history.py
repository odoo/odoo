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
    package_id = fields.Many2one('stock.package', 'Package', required=True, index=True, ondelete='cascade')
    package_name = fields.Char('Package Name', required=True)
    package_type_id = fields.Many2one('stock.package.type', related='package_id.package_type_id')
    parent_orig_id = fields.Many2one('stock.package', 'Origin Container')
    parent_orig_name = fields.Char('Origin Container Name')
    parent_dest_id = fields.Many2one('stock.package', 'Destination Container')
    parent_dest_name = fields.Char('Destination Container Name')
    outermost_dest_id = fields.Many2one('stock.package', 'Outermost Destination Container')
    picking_ids = fields.Many2many('stock.picking', string='Transfers')

    def _get_all_history_children_package_dest_ids(self):
        """
        Gets all child packages using history records of packages recursively.
        Should be the same as stock_package._get_all_children_package_dest_ids() but this method
        uses history records (used when pickings are done) and returns as dict the direct children
        only per package (not all children per package) and the set of all child packages.
        :returns: A dict mapping each package in self to a list of its direct child packages
        :returns: A set of all child packages
        """
        all_children_ids = set(self.package_id.ids)
        direct_children_by_pack = {}

        histories_by_parent_pack = self.grouped('parent_dest_id')
        for history in self:
            children = histories_by_parent_pack.get(history.package_id)
            if children:
                direct_children_by_pack[history.package_id.id] = children.package_id

        return direct_children_by_pack, all_children_ids

    def _get_complete_dest_name_except_outermost(self):
        self.ensure_one()
        if not self.parent_dest_id:
            return ''
        elif self.parent_dest_id == self.outermost_dest_id:
            return self.package_id.name

        # Complete name without the first (outermost) package name
        return ' > '.join(self.package_name.split(' > ')[1:])

    def action_show_package(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'stock.package',
            'res_id': self.package_id.id,
        }
