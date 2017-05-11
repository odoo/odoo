# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class AccountConfigSettings(models.TransientModel):
    _inherit = 'account.config.settings'

    use_out_inv_comm = fields.Boolean(string='Structured Communication', related='company_id.use_out_inv_comm')
    out_inv_comm_type = fields.Selection(related='company_id.out_inv_comm_type', change_default=True,
        help='Select Default Communication Type for Outgoing Invoices.', default='none')
    out_inv_comm_algorithm = fields.Selection([
        ('random', 'Random'),
        ('date', 'Date'),
        ('partner_ref', 'Customer Reference'),
        ], string='Communication Algorithm',
        related='company_id.out_inv_comm_algorithm',
        help='Select Algorithm to generate the Structured Communication on Outgoing Invoices.')

    @api.onchange('use_out_inv_comm')
    def _onchange_use_out_inv_comm(self):
        if self.use_out_inv_comm:
            self.out_inv_comm_type = 'bba'
        else:
            self.out_inv_comm_type = 'none'
