from odoo import api, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        info['approvals.mail_activity_data_approval'] = {
            'res_model': 'approval.request',
            'unlink': False,
        }
        return info
