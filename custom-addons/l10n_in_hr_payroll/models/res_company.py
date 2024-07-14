# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_dearness_allowance = fields.Boolean(string='Dearness Allowance', default=True,
        help='Check this box if your company provide Dearness Allowance to employee')
