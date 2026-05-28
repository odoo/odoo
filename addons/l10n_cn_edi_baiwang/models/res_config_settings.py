# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models

from .baiwang_client import BaiwangClient


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_cn_edi_mode = fields.Selection(related="company_id.l10n_cn_edi_mode", readonly=False)
    l10n_cn_edi_company_vat = fields.Char(string="Company Tax ID", related="company_id.vat")
    l10n_cn_accept_processing = fields.Boolean()
    l10n_cn_baiwang_app_key = fields.Char(related="company_id.l10n_cn_baiwang_app_key", readonly=False)
    l10n_cn_baiwang_app_secret = fields.Char(related="company_id.l10n_cn_baiwang_app_secret", readonly=False)
    l10n_cn_baiwang_username = fields.Char(related="company_id.l10n_cn_baiwang_username", readonly=False)
    l10n_cn_baiwang_password = fields.Char(related="company_id.l10n_cn_baiwang_password", readonly=False)
    l10n_cn_baiwang_salt = fields.Char(related="company_id.l10n_cn_baiwang_salt", readonly=False)
    l10n_cn_baiwang_org_auth_code = fields.Char(related="company_id.l10n_cn_baiwang_org_auth_code", readonly=False)

    # ----------------
    # Action methods
    # ----------------

    def action_l10n_cn_baiwang_test_connection(self):
        """Test Baiwang API connection by attempting OAuth token retrieval."""
        self.ensure_one()
        # Save pending changes first
        self.execute()
        client = BaiwangClient(self.company_id)
        client._get_token()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Connection Successful",
                'message': "Successfully authenticated with Baiwang API.",
                'type': 'success',
                'sticky': False,
            },
        }

    def action_open_company_form(self):
        """ This will be used to ease the configuration by allowing to quickly access the company. """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.env.company.id,
            'res_model': 'res.company',
            'target': 'new',
            'view_mode': 'form',
        }
