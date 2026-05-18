# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_baiwang_app_key = fields.Char(string="Baiwang App Key")
    l10n_cn_baiwang_app_secret = fields.Char(string="Baiwang App Secret")
    l10n_cn_baiwang_salt = fields.Char(string="Baiwang Salt")
    l10n_cn_baiwang_cached_token = fields.Char(string="Baiwang Token")
    l10n_cn_edi_mode = fields.Selection(
        selection=[
            ('test', 'Pre-Production'),
            ('prod', 'Production'),
        ],
        # Nothing will happen until the user register, so it can be set by default.
        default="test",
    )

    # ----------------
    # Business methods
    # ----------------
