# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    aba_routing = fields.Char(
        string="ABA/Routing",
        pattern=r'^\d{1,9}$',
        help="American Bankers Association Routing Number. Maximum 9 digits.",
    )
