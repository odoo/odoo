import re

from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_debug = DebugLog(__name__)

_CODE_SEPARATORS = re.compile(r"[^A-Z0-9]+")


class MixinTag(models.AbstractModel):
    _name = "mixin.tag"
    _inherit = ["mixin.catalog", "mixin.color"]
    _description = "Tag (coloured label with a stable code)"
    _order = "name, id"

    name = fields.Char(string="Tag Name")
    active = fields.Boolean(help="Archive a tag to hide it without deleting it.")
    color = fields.Integer(
        default=lambda self: self._default_color(),
        aggregator=False,
    )
    code = fields.Char(
        compute="_compute_code",
        store=True,
        index="btree",
        copy=False,
        readonly=False,
        help="Stable identifier for imports, filters and data files. Unlike the "
        "name it is never translated, so it means the same thing to every "
        "reader.",
    )
    _code_uniq = models.Constraint(
        "unique(code)",
        "A tag with this code already exists.",
    )

    @api.depends("name")
    def _compute_code(self):
        pending = self.filtered(lambda tag: not tag.code and tag.name)
        self.filtered(lambda tag: not tag.code and not tag.name).code = False
        if not pending:
            _debug.logic(
                "codes_kept", model=self._name, tags=len(self), reason="none_pending"
            )
            return
        taken = {
            code
            for [code] in self.env.execute_query(
                SQL(
                    "SELECT code FROM %s WHERE code IS NOT NULL",
                    SQL.identifier(self._table),
                )
            )
        }
        suffixed = 0  # debuglog
        for tag in pending:
            base = self._name_to_code(tag.name) or "TAG"
            candidate, suffix = base, 1
            while candidate in taken:
                suffix += 1
                candidate = f"{base}_{suffix}"
            suffixed += candidate != base  # debuglog
            taken.add(candidate)
            tag.code = candidate
        _debug.logic(
            "codes_generated",
            model=self._name,
            pending=len(pending),
            taken=len(taken),
            suffixed=suffixed,
        )

    @api.model
    def _name_to_code(self, name):
        return _CODE_SEPARATORS.sub("_", (name or "").upper()).strip("_")[:64]
