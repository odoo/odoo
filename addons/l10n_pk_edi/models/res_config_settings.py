# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    l10n_pk_edi_pos_key = fields.Char("PoS ID", related="company_id.l10n_pk_edi_pos_key", readonly=False)
    l10n_pk_edi_token = fields.Char("Pakistan EDI Token", related="company_id.l10n_pk_edi_token", readonly=False)
    # This proxy is only to access FBR APIs from out side of Pakistan for testing purpose.
    # And will remove before stable release. (Use proxy server of USA and Dubai to access)
    l10n_pk_edi_proxy = fields.Char("HTTPS Proxy", related="company_id.l10n_pk_edi_proxy", readonly=False)
