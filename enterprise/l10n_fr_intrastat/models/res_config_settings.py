# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_fr_intrastat_envelope_id = fields.Char(
        string="DEBWEB2 Identifier",
        related='company_id.l10n_fr_intrastat_envelope_id',
        readonly=False
    )
