from odoo import fields, models
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pk_iap_server_ip = fields.Char(related='company_id.l10n_pk_iap_server_ip')

    def action_refresh_l10n_pk_iap_server_ip(self):
        server_ip = self.company_id._get_iap_server_ip()
        if not server_ip:
            raise UserError(self.env._(
                "Could not resolve the address of the Odoo IAP service. Please try again later.",
            ))
        self.company_id.l10n_pk_iap_server_ip = server_ip
