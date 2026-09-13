import typing

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .mail_message import MailMessage

_debug = DebugLog(__name__)


class MailMessageTranslation(models.Model):
    _name = "mail.message.translation"
    _description = "Message Translation"

    message_id: MailMessage = fields.Many2one(
        comodel_name="mail.message",
        required=True,
        ondelete="cascade",
    )
    source_lang = fields.Char(
        string="Source Language",
        required=True,
        help="Result of the language detection based on its content.",
    )
    target_lang = fields.Char(
        string="Target Language",
        required=True,
        help="Shortened language code used as the target for the translation request.",
    )
    body = fields.Html(
        string="Translation Body",
        sanitize_style=True,
        required=True,
        help="String received from the translation request.",
    )
    create_date = fields.Datetime(index=True)

    _unique = models.UniqueIndex("(message_id, target_lang)")

    @api.autovacuum
    def _gc_translations(self) -> None:
        treshold = fields.Datetime().now() - relativedelta(weeks=2)
        stale = self.search([("create_date", "<", treshold)])
        _debug.lifecycle("gc_translations", removed=len(stale))
        stale.unlink()
