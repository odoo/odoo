# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_pk_edi_pos_key = fields.Char("PoS ID", groups="base.group_system")
    l10n_pk_edi_token = fields.Char("E-invoice (PK) Token", groups="base.group_system")
    # This proxy is only to access FBR APIs from out side of Pakistan for testing purpose.
    # And will remove before stable release. (Use proxy server of USA and Dubai to access)
    l10n_pk_edi_proxy = fields.Char("HTTPS Proxy", groups="base.group_system")
