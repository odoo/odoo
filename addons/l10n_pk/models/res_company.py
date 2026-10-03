import socket
from urllib.parse import urlsplit

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # Single value shared by the whole instance, kept in a system parameter rather than per company.
    l10n_pk_iap_server_ip = fields.Char(string="Odoo Static IP Address", compute='_compute_l10n_pk_iap_server_ip', inverse='_inverse_l10n_pk_iap_server_ip')

    def _compute_l10n_pk_iap_server_ip(self):
        server_ip = self.env['ir.config_parameter'].sudo().get_str('l10n_pk.iap_server_ip', '')
        for company in self:
            company.l10n_pk_iap_server_ip = server_ip

    def _inverse_l10n_pk_iap_server_ip(self):
        for company in self:
            self.env['ir.config_parameter'].sudo().set_str('l10n_pk.iap_server_ip', company.l10n_pk_iap_server_ip or '')

    def _get_iap_server_ip(self):
        iap_endpoint = self.env['ir.config_parameter'].sudo().get_str('l10n_pk.iap_endpoint')
        try:
            hostname = urlsplit(iap_endpoint).hostname
            return socket.gethostbyname(hostname)
        except (socket.gaierror, AttributeError):
            return False

    @api.model
    def _l10n_pk_edi_action_activate(self):
        """Install the Pakistan e-invoicing module, then land the user on its settings."""
        module = self.env['ir.module.module']._get('l10n_pk_edi')
        if module.state != 'installed':
            module.button_immediate_install()
        # The install adds menus and views, so the client has to be reloaded to pick them up.
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
            'params': {'action_id': self.env.ref('account.action_account_config').id},
        }
