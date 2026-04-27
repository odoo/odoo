# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _to_store(self, store, /, *, fields=None, extra_fields=None):
        if not self.env.user._is_portal():
            super()._to_store(store, fields=fields, extra_fields=extra_fields)
            return

        def knowledge_attachment_requires_token(attachment):
            return (
                attachment.res_model == 'knowledge.article.thread' and
                self.env['knowledge.article.thread'].sudo(False).with_user(self.env.user)
                    .browse(attachment.res_id).has_access('read')
            )

        # Add access_token to the knowledge article's attachments for portal users
        knowledge_attachments = self.filtered(knowledge_attachment_requires_token)
        super(IrAttachment, self - knowledge_attachments)._to_store(store, fields=fields, extra_fields=extra_fields)
        extra_fields = extra_fields or []
        if "access_token" not in extra_fields:
            extra_fields.append("access_token")
        super(IrAttachment, knowledge_attachments)._to_store(store, fields=fields, extra_fields=extra_fields)
