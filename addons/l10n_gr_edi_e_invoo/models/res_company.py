from odoo import models

from .account_edi_proxy_user import L10N_GR_EDI_PROXY_TYPE


class ResCompany(models.Model):
    _inherit = 'res.company'

    def _l10n_gr_edi_get_or_create_proxy_user(self):
        self.ensure_one()
        edi_mode = 'test' if self.l10n_gr_edi_test_env else 'prod'

        domain = [
            ('company_id', '=', self.id),
            ('proxy_type', '=', L10N_GR_EDI_PROXY_TYPE),
            ('edi_mode', '=', edi_mode),
        ]
        proxy_user_sudo = self.env['account_edi_proxy_client.user'].sudo()
        if proxy_user := proxy_user_sudo.search(domain, limit=1):
            return proxy_user, False

        self._with_locked_records(self)
        # Another worker may have created and committed the proxy user between
        # the first search and acquiring the lock so we need to check again.
        if proxy_user := proxy_user_sudo.search(domain, limit=1):
            return proxy_user, False

        proxy_user = proxy_user_sudo._register_proxy_user(self, L10N_GR_EDI_PROXY_TYPE, edi_mode)
        return proxy_user, True

    def _l10n_gr_edi_get_proxy_user(self):
        self.ensure_one()
        proxy_user, registration_created = self._l10n_gr_edi_get_or_create_proxy_user()
        if registration_created and self.env['account.move']._can_commit():
            self.env.cr.commit()
        return proxy_user
