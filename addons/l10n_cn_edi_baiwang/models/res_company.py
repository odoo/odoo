# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    # Baiwang API credentials
    l10n_cn_baiwang_app_key = fields.Char(string="App Key")
    l10n_cn_baiwang_app_secret = fields.Char(string="App Secret")
    l10n_cn_baiwang_username = fields.Char(string="Username")
    l10n_cn_baiwang_password = fields.Char(string="Password")
    l10n_cn_baiwang_salt = fields.Char(string="Salt", help="User salt for password hashing (provided during Baiwang account setup)")
    l10n_cn_baiwang_org_auth_code = fields.Char(
        string="Org Auth Code",
        help="Unique enterprise identifier issued by Baiwang. Required for third-party apps; "
             "optional for internal enterprise apps. Found in Developer Portal → App Management → Permissions → Authorized Enterprises.",
    )
    l10n_cn_baiwang_invoice_terminal_code = fields.Char(string="Invoice Terminal Code", help="Only needed for tax-controlled invoices (004/007/028)")

    # Token management (auto-managed)
    l10n_cn_baiwang_cached_token = fields.Char(string="Cached Token", copy=False)
    l10n_cn_baiwang_refresh_token = fields.Char(string="Refresh Token", copy=False)
    l10n_cn_baiwang_token_expiry = fields.Datetime(string="Token Expiry", copy=False)

    # Mode
    l10n_cn_edi_mode = fields.Selection(
        selection=[
            ('test', 'Pre-Production (Sandbox)'),
            ('prod', 'Production'),
        ],
        default='test',
        string="Baiwang Mode",
    )
