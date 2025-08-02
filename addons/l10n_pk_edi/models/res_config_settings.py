# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pk_edi_pos_key = fields.Char(related='company_id.l10n_pk_edi_pos_key', readonly=False)
    l10n_pk_edi_token = fields.Char(related='company_id.l10n_pk_edi_token', readonly=False)
