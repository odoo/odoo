# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_lu_official_social_security = fields.Char(related='company_id.l10n_lu_official_social_security', readonly=False)
    l10n_lu_seculine = fields.Char(related='company_id.l10n_lu_seculine', readonly=False)
