# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _get_comm_type(self):
        return self.env['account.invoice']._get_reference_type()

    out_inv_comm_type = fields.Selection('_get_comm_type', string='Communication Type', change_default=True, default='none')
    out_inv_comm_algorithm = fields.Selection([
        ('none', "None"),
        ('random', "Random Reference"),
        ('date', "Based on Invoice's Creation Date"),
        ('partner_ref', "Based on Customer's Internal Reference"),
        ], string='Communication Algorithm', default='none',
        help="Choose an algorithm to generate the structured communication.")
