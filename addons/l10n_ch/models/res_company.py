# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class Company(models.Model):
    _inherit = "res.company"

    l10n_ch_isr_print_bank_location = fields.Boolean(string='Print bank location', default=False, help='Boolean option field indicating whether or not the alternate layout (the one printing bank name and address) must be used when generating an ISR.')
