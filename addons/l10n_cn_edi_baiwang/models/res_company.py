# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    # Baiwang API credentials
    l10n_cn_baiwang_app_key = fields.Char(string="Baiwang App Key")
    l10n_cn_baiwang_app_secret = fields.Char(string="Baiwang App Secret")
    l10n_cn_baiwang_username = fields.Char(string="Baiwang Username")
    l10n_cn_baiwang_password = fields.Char(string="Baiwang Password")
    l10n_cn_baiwang_salt = fields.Char(string="Baiwang Salt", help="User salt for password hashing (provided during Baiwang account setup)")
    l10n_cn_baiwang_tax_no = fields.Char(string="Baiwang Tax No", help="Seller tax registration number (销方税号) registered with Baiwang")
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
