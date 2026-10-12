# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')
