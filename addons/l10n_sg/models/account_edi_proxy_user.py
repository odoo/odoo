from odoo import models


class AccountEdiProxyUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_get_participant_status(self):
        sg_receiver_domain = [
            ('company_id.account_peppol_proxy_state', '=', 'receiver'),
            ('company_id.routing_scheme', '=', '0195'),
        ]
        prev_sg_receivers = self.filtered_domain(sg_receiver_domain)
        super()._peppol_get_participant_status()
        new_sg_receivers = self.filtered_domain(sg_receiver_domain) - prev_sg_receivers
        if new_sg_receivers:
            cron = self.env.ref(
                'account_peppol.ir_cron_peppol_auto_register_services',
                raise_if_not_found=False,
            )
            if cron:
                cron._trigger()
