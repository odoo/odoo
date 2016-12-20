# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    po_lead = fields.Float(related='company_id.po_lead', default=lambda self: self.env.user.company_id.po_lead)
    default_new_po_lead = fields.Boolean(string="Security Lead Time for Purchase", default_model="stock.config.settings", help="Margin of error for vendor lead times. When the system generates Purchase Orders for reordering products,they will be scheduled that many days earlier to cope with unexpected vendor delays.")
