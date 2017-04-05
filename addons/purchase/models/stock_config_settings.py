# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockConfigSettings(models.TransientModel):
    _inherit = 'stock.config.settings'

    po_lead = fields.Float(related='company_id.po_lead', default=lambda self: self.env.user.company_id.po_lead)
    use_po_lead = fields.Boolean(
        string="Security Lead Time for Purchase",
        oldname='default_new_po_lead',
        help="Margin of error for vendor lead times. When the system generates Purchase Orders for reordering products,they will be scheduled that many days earlier to cope with unexpected vendor delays.")

    @api.onchange('use_po_lead')
    def _onchange_use_po_lead(self):
        if not self.use_po_lead:
            self.po_lead = 0.0

    def get_default_fields(self, fields):
        return dict(
            use_po_lead=self.env['ir.config_parameter'].sudo().get_param('purchase.use_po_lead')
        )

    def set_fields(self):
        self.env['ir.config_parameter'].sudo().set_param('purchase.use_po_lead', self.use_po_lead)
