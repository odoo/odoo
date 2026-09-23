import logging
import typing

from odoo import fields, models
from odoo.libs.debug_log import DebugLog

if typing.TYPE_CHECKING:
    from .mail_alias import MailAlias

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class MixinMailAlias(models.AbstractModel):
    _name = "mixin.mail.alias"
    _inherit = ["mixin.mail.alias.optional"]
    _inherits = {"mail.alias": "alias_id"}
    _description = "Email Aliases Mixin"
    _inherits_rules = False

    alias_id: MailAlias = fields.Many2one(required=True)
    alias_name = fields.Char(inherited=True)
    alias_defaults = fields.Text(inherited=True)

    def _is_new_alias_required(self, record_vals: dict) -> bool:
        return not record_vals.get("alias_id")

    def _init_column(self, name: str, *, new_column: bool = False) -> None:
        super()._init_column(name, new_column=new_column)
        if name == "alias_id":
            self.pool.post_init(self._init_column_alias_id)

    def _init_column_alias_id(self) -> None:
        child_ctx = {
            "active_test": False,
            "prefetch_fields": False,
        }
        child_model = self.sudo().with_context(child_ctx)

        orphans = child_model.search([("alias_id", "=", False)])
        _debug.lifecycle(
            "alias_column_initialized", model=self._name, records=len(orphans)
        )
        for record in orphans:
            record_company = record._mail_get_companies()[record.id]
            alias = (
                self.env["mail.alias"]
                .sudo()
                .with_company(record_company)
                .create(record._alias_get_creation_values())
            )
            record.with_context(mail_notrack=True).alias_id = alias
            _logger.info(
                "Mail alias created for %s %s (id %s)",
                record._name,
                record.display_name,
                record.id,
            )
