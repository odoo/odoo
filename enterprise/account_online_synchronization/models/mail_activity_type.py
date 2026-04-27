from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        info['account_online_synchronization.bank_sync_activity_update_consent'] = {
            'res_model': 'account.journal',
            'unlink': False,
        }
        return info
