# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_comm_type(self):
        return self.env['account.invoice']._get_reference_type()

    use_out_inv_comm = fields.Boolean(string='Structured Communication')
    out_inv_comm_type = fields.Selection('_get_comm_type', string='Communication Type', change_default=True, default='none')
    out_inv_comm_algorithm = fields.Selection([
        ('random', 'Random'),
        ('date', 'Date'),
        ('partner_ref', 'Customer Reference'),
        ], string='Communication Algorithm', default='random',
        help='Select Algorithm to generate the Structured Communication on Outgoing Invoices.')
