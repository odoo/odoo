# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_lt_official_social_security = fields.Char(
        string="Social Security Number", related='company_id.l10n_lt_official_social_security', readonly=False)
