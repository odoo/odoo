from odoo import models


class MailThread(models.AbstractModel):
    _inherit = ['mail.thread']

    def _prepare_attachment_post_values(self, content, name, model, res_id, extra_info):
        return dict(super()._prepare_attachment_post_values(content, name, model, res_id, extra_info), is_voice=(extra_info or {}).get('is_voice'))
