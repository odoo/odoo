from odoo import api, models, fields


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('grant_approval', 'Grant Approval')], ondelete={'grant_approval': 'set default'})

    @api.model
    def _get_model_info_by_xmlid(self):
        info = super()._get_model_info_by_xmlid()
        info['web_studio.mail_activity_data_approve'] = {
            'res_model': False,
            'unlink': False,
        }
        return info
