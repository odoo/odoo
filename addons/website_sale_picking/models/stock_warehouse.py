# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    opening_hours = fields.Many2one(
        string="Opening hours",
        comodel_name='resource.calendar',
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )
