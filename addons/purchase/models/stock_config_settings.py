# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    po_lead = fields.Float(related='company_id.po_lead')
    use_po_lead = fields.Boolean(
        string="Security Lead Time for Purchase",
        oldname='default_new_po_lead',
        help="Margin of error for vendor lead times. When the system generates Purchase Orders for reordering products,they will be scheduled that many days earlier to cope with unexpected vendor delays.")

    @api.onchange('use_po_lead')
    def _onchange_use_po_lead(self):
        if not self.use_po_lead:
            self.po_lead = 0.0

    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            use_po_lead=self.env['ir.config_parameter'].sudo().get_param('purchase.use_po_lead')
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('purchase.use_po_lead', self.use_po_lead)
