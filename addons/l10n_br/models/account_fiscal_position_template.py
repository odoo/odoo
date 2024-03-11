# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountFiscalPositionTemplate(models.Model):
    _inherit = 'account.fiscal.position.template'

    l10n_br_fp_type = fields.Selection(
        selection=[
            ('internal', 'Internal'),
            ('ss_nnm', 'South/Southeast selling to North/Northeast/Midwest'),
            ('interstate', 'Other interstate'),
        ],
        string='Interstate Fiscal Position Type',
    )
