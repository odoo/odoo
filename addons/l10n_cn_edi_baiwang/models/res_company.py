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

    # Mode
    l10n_cn_edi_mode = fields.Selection(
        selection=[
            ('test', 'Pre-Production (Sandbox)'),
            ('prod', 'Production'),
        ],
        default='test',
        string="Baiwang Mode",
    )
    l10n_cn_baiwang_drawer = fields.Char(
        string="Drawer (开票人)",
        help="Name printed as the drawer (开票人) on issued Baiwang e-Fapiao. "
             "Defaults to the current user when left empty.",
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
            self.env['account_edi_proxy_client.user']._l10n_cn_baiwang_create_proxy_user(
                self,
                self.l10n_cn_edi_mode,
            )
            self._compute_l10n_cn_baiwang_proxy_user_id()
        return self.l10n_cn_baiwang_proxy_user_id
