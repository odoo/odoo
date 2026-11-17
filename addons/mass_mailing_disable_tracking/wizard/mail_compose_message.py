from odoo import models


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    def _prepare_mail_values_dynamic(self, res_ids):
        res = super()._prepare_mail_values_dynamic(res_ids)
        mailing = self.mass_mailing_id
        if not mailing or self.composition_mode != 'mass_mail':
            return res
        open_blocked = mailing._get_open_tracking_blocked_res_ids(self.model, res_ids)
        click_blocked = mailing._get_click_tracking_blocked_res_ids(self.model, res_ids)
        for res_id in res_ids:
            res[res_id]['block_open_tracking'] = res_id in open_blocked
            res[res_id]['block_click_tracking'] = res_id in click_blocked
        return res
