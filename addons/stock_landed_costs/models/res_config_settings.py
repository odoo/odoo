# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    lc_journal_id = fields.Many2one('account.journal', string='Default Journal', related='company_id.lc_journal_id', readonly=False)

