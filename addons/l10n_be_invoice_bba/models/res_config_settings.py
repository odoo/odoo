# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    out_inv_comm_type = fields.Selection(related='company_id.out_inv_comm_type', change_default=True,
        help='Select Default Communication Type for Outgoing Invoices.', default='none')
    out_inv_comm_algorithm = fields.Selection([
        ('none', "None"),
        ('random', "Random Reference"),
        ('date', "Based on Invoice's Creation Date"),
        ('partner_ref', "Based on Customer's Internal Reference"),
        ], string='Communication Algorithm',
        related='company_id.out_inv_comm_algorithm',
        help="Choose an algorithm to generate the structured communication.")

    @api.onchange('out_inv_comm_algorithm')
    def _onchange_out_inv_comm_algorithm(self):
        if self.out_inv_comm_algorithm == 'none':
            self.out_inv_comm_type = 'none'
        else:
            self.out_inv_comm_type = 'bba'
