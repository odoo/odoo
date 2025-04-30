from odoo import fields, models


class MailMessageIrAttachment(models.Model):
    _name = "mail.message.attachment"
    _description = "Link table between attachment and message"
    _table = "message_attachment_rel"

    message_id = fields.Many2one("mail.message", required=True)
    attachment_id = fields.Many2one("ir.attachment", required=True)

    thumbnail = fields.Binary(string="Generated thumbnail", attachment=True)
