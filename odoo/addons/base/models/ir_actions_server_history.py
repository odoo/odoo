import babel

from odoo import api, fields, models
from odoo.libs.datetime import utc
from odoo.libs.debug_log import DebugLog
from odoo.tools import _, get_lang

_debug = DebugLog(__name__)


class IrActionsServerHistory(models.Model):
    _name = "ir.actions.server.history"
    _description = "Server Action History"
    _order = "create_date desc, id desc"
    _max_entries_per_action = 100

    action_id = fields.Many2one(
        comodel_name="ir.actions.server",
        required=True,
        ondelete="cascade",
    )
    code = fields.Text()

    @api.depends("create_date", "create_uid")
    @api.depends_context("lang", "tz")
    def _compute_display_name(self) -> None:
        self.display_name = False
        locale = get_lang(self.env).code
        tzinfo = self.env.tz
        for history in self.filtered("create_date"):
            dt = history.create_date.replace(microsecond=0, tzinfo=utc)
            if tzinfo:
                dt = dt.astimezone(tzinfo)
            date_label = babel.dates.format_datetime(
                dt,
                tzinfo=tzinfo,
                locale=locale,
            )
            history.display_name = _(
                "%(date_label)s - %(author)s",
                date_label=date_label,
                author=history.create_uid.name,
            )

    @api.autovacuum
    def _gc_histories(self) -> None:
        result = self._read_group(
            domain=[],
            groupby=["action_id"],
            aggregates=["id:recordset"],
            having=[("__count", ">", self._max_entries_per_action)],
        )
        to_clean = self
        for _action_id, history_ids in result:
            to_clean |= history_ids.sorted()[self._max_entries_per_action :]
        _debug.lifecycle("gc_histories", actions=len(result), removed=len(to_clean))
        to_clean.unlink()


WEBHOOK_SAMPLE_VALUES = {
    "integer": 42,
    "float": 42.42,
    "monetary": 42.42,
    "char": "Hello World",
    "text": "Hello World",
    "html": "<p>Hello World</p>",
    "boolean": True,
    "selection": "option1",
    "date": "2020-01-01",
    "datetime": "2020-01-01 00:00:00",
    "binary": "<base64_data>",
    "many2one": 47,
    "many2many": [42, 47],
    "one2many": [42, 47],
    "reference": "res.partner,42",
    None: "some_data",
}

CRUD_STATES = ("object_write", "object_create", "object_copy")
