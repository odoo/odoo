# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class MailMessageTranslation(models.Model):
    _name = 'mail.message.translation'
    _description = "Message Translation"

    message_id = fields.Many2one("mail.message", "Message", required=True, ondelete="cascade")
    source_lang = fields.Char(
        "Source Language", required=True, help="Result of the language detection based on its content."
    )
    target_lang = fields.Char(
        "Target Language", required=True, help="Shortened language code used as the target for the translation request."
    )
    body = fields.Html(
        "Translation Body", required=True, sanitize_style=True, help="String received from the translation request."
    )
    create_date = fields.Datetime(index=True)

    _unique = models.UniqueIndex("(message_id, target_lang)")

    @api.autovacuum
    def _gc_translations(self):
        treshold = fields.Datetime().now() - relativedelta(weeks=2)
        self.search([("create_date", "<", treshold)]).unlink()
