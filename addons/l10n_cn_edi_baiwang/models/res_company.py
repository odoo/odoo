# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_baiwang_org_auth_code = fields.Char(
        string="Org Auth Code",
        help="Unique enterprise identifier issued by Baiwang. Required for third-party apps; "
             "optional for internal enterprise apps. Found in Developer Portal → App Management → Permissions → Authorized Enterprises.",
    )
    l10n_cn_baiwang_subscription_status = fields.Selection(
        selection=[
            ('not_subscribed', 'Not Subscribed'),
            ('subscribed', 'Subscribed'),
            ('authorized', 'Authorized'),
        ],
        string="Baiwang Registration Status",
        default='not_subscribed',
        copy=False,
    )
    l10n_cn_baiwang_proxy_user_id = fields.Many2one(
        comodel_name='account_edi_proxy_client.user',
        compute='_compute_l10n_cn_baiwang_proxy_user_id',
    )
    l10n_cn_baiwang_last_request_id = fields.Char(copy=False)

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

    @api.depends('account_edi_proxy_client_ids', 'l10n_cn_edi_mode')
    def _compute_l10n_cn_baiwang_proxy_user_id(self):
        for company in self:
            company.l10n_cn_baiwang_proxy_user_id = company.account_edi_proxy_client_ids.filtered(
                lambda user: user.proxy_type == 'l10n_cn_edi_baiwang' and user.edi_mode == company.l10n_cn_edi_mode,
            )[:1]

    def _l10n_cn_baiwang_create_proxy_user(self):
        self.ensure_one()
        if not self.l10n_cn_baiwang_proxy_user_id:
            self.env['account_edi_proxy_client.user']._register_proxy_user(
                self,
                'l10n_cn_edi_baiwang',
                self.l10n_cn_edi_mode,
            )
            self._compute_l10n_cn_baiwang_proxy_user_id()
        return self.l10n_cn_baiwang_proxy_user_id
