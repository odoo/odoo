# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_th_edi_inet_staging_mode = fields.Boolean(
        related='company_id.l10n_th_edi_inet_staging_mode',
        readonly=False,
    )
    l10n_th_edi_inet_api_key = fields.Char(
        related='company_id.l10n_th_edi_inet_api_key',
        readonly=False,
    )
    l10n_th_edi_inet_authorization_code = fields.Char(
        related='company_id.l10n_th_edi_inet_authorization_code',
        readonly=False,
    )
    l10n_th_edi_subdistrict_code = fields.Char(
        related='company_id.l10n_th_edi_subdistrict_code',
        readonly=False,
    )
