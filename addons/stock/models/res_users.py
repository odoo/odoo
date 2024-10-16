# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import digest


class ResUsers(digest.ResUsers):

    def _get_default_warehouse_id(self):
        # !!! Any change to the following search domain should probably
        # be also applied in sale_stock/models/sale_order.py/_init_column.
        return self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
