# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pe_chart_of_accounts = fields.Selection(
        related="company_id.l10n_pe_chart_of_accounts",
        readonly=False,
    )
