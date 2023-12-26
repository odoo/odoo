# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class IrModule(models.Model):
    _inherit = 'ir.module.module'


    @api.returns('self')
    def downstream_dependencies(
            self,
            known_deps=None,
            exclude_states=('uninstalled', 'uninstallable', 'to remove'),
            ):
        # sale_stock_margin implicitly depends on sale_stock, but sale_stock is not marked as one of
        # its dependencies, thus uninstalling sale_stock without uninstalling sale_stock_margin
        # will make the registry crash, the install works purely because sale_stock is auto-installed
        # when the dependencies of sale_stock_margin are installed
        if 'sale_stock' in self.mapped('name'):
            # we force sale_stock_margin as a dependant of sale_stock
            known_deps = (known_deps or self.browse()) | self.search([
                ('name', '=', 'sale_stock_margin'),
                ('state', '=', 'installed'),
            ], limit=1)
        return super().downstream_dependencies(known_deps, exclude_states)
