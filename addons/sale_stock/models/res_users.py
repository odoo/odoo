# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    property_warehouse_id = fields.Many2one('stock.warehouse', string='Default Warehouse', company_dependent=True, check_company=True, user_writeable=True)

    def _get_default_warehouse_id(self):
        if self.property_warehouse_id:
            return self.property_warehouse_id
        return super()._get_default_warehouse_id()
