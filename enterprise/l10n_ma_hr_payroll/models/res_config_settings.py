# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_ma_employer_contribution = fields.Float(related="company_id.l10n_ma_employer_contribution")
    l10n_ma_social_security_organization = fields.Char(related="company_id.l10n_ma_social_security_organization")
    l10n_ma_collective_agreement = fields.Char(related="company_id.l10n_ma_collective_agreement")
