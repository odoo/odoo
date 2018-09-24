# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_be_structured_comm = fields.Selection(related='company_id.l10n_be_structured_comm', readonly=False,
        string='Communication Algorithm', default='random',
        help='Choose an algorithm to generate the structured communication.')
