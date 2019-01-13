# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _get_invoice_reference_types(self):
        # OVERRIDE
        res = super(ResCompany, self)._get_invoice_reference_types()
        res.append(('structured', 'Structured Communication'))
        return res

    l10n_be_structured_comm = fields.Selection([
        ('random', "Random Reference"),
        ('date', "Based on Invoice's Creation Date"),
        ('partner_ref', "Based on Customer's Internal Reference"),
    ], string='Communication Algorithm', default='random', help='Choose an algorithm to generate the structured communication.')
