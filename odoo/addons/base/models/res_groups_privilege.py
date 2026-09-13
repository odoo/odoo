from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResGroupsPrivilege(models.Model):
    _name = "res.groups.privilege"
    _description = "Privileges"
    _order = "sequence, name, id"

    name = fields.Char(
        translate=True,
        required=True,
    )
    description = fields.Text()
    placeholder = fields.Char(
        default="No",
        help="Label shown for the empty option in the privilege selection field of the user form (e.g. 'No' access).",
    )
    sequence = fields.Integer(default=100)
    category_id = fields.Many2one(
        comodel_name="ir.module.category",
        index=True,
    )
    group_ids = fields.One2many(
        comodel_name="res.groups",
        inverse_name="privilege_id",
        string="Groups",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        records = super().create(vals_list)
        _debug.lifecycle("create", count=len(records))
        self.env.registry.clear_cache("groups")
        return records

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        res = super().write(vals)
        self.env.registry.clear_cache("groups")
        return res

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self))
        res = super().unlink()
        self.env.registry.clear_cache("groups")
        return res
