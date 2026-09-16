from typing import Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class IrModuleModuleExclusion(models.Model):
    _name = "ir.module.module.exclusion"
    _inherit = ["mixin.module.link"]
    _description = "Module exclusion"
    _log_access = False

    linked_id = fields.Many2one(string="Excluded Module")

    _module_exclusion_uniq = models.UniqueIndex(
        "(module_id, name) WHERE module_id IS NOT NULL AND name IS NOT NULL",
        "A module cannot declare the same exclusion twice!",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        records = super().create(vals_list)
        _debug.lifecycle("create", count=len(records))
        return records

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", count=len(self))
        return super().unlink()
