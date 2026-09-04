from odoo import models


class AccountEdiProxyUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_get_participant_status(self):
        prev_receivers = self.filtered(
            lambda u: u.company_id.account_peppol_proxy_state == 'receiver'
        )
        super()._peppol_get_participant_status()
        new_sg_receivers = self.filtered(
            lambda u: u not in prev_receivers
            and u.company_id.account_peppol_proxy_state == 'receiver'
            and u.company_id.routing_scheme == '0195'
        )
        if new_sg_receivers:
            cron = self.env.ref(
                'account_peppol.ir_cron_peppol_auto_register_services',
                raise_if_not_found=False,
            )
            if cron:
                cron._trigger()
