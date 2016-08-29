# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    vat_check_vies = fields.Boolean(
        string='VIES VAT Check',
        help="If checked, Partners VAT numbers will be fully validated against EU's VIES service "
             "rather than via a simple format validation (checksum).")
