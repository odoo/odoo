from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post_with_view(self, views_or_xmlid, **kwargs):
        super(MailThread, self.with_context(inherit_branding=False)).message_post_with_view(views_or_xmlid, **kwargs)
