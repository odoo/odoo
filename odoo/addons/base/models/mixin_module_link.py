from collections.abc import Iterable
from typing import Any

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from .ir_module import LINK_STATES

_debug = DebugLog(__name__)


class MixinModuleLink(models.AbstractModel):
    _name = "mixin.module.link"
    _description = "Module link (a module named by another module's manifest)"
    _log_access = False
    _allow_sudo_commands = False

    name = fields.Char(index=True)
    module_id = fields.Many2one(
        comodel_name="ir.module.module",
        ondelete="cascade",
    )
    linked_id = fields.Many2one(
        comodel_name="ir.module.module",
        string="Linked Module",
        compute="_compute_linked_id",
        search="_search_linked_id",
    )
    state = fields.Selection(
        selection=LINK_STATES,
        string="Status",
        compute="_compute_state",
    )

    @api.depends("name")
    def _compute_linked_id(self) -> None:
        modules = self.env["ir.module.module"].search(
            [("name", "in", list({link.name for link in self}))]
        )
        by_name = {module.name: module for module in modules}
        _debug.perf.count(
            "linked_modules_resolved",
            model=self._name,
            links=len(self),
            modules=len(modules),
        )
        for link in self:
            link.linked_id = by_name.get(link.name)

    def _search_linked_id(self, operator: str, value: Any) -> Domain:
        Module = self.env["ir.module.module"]
        if operator in ("any", "not any"):
            names = list(Module.search(Domain(value)).mapped("name"))
            _debug.logic(
                "linked_id_search",
                model=self._name,
                operator=operator,
                names=len(names),
            )
            return Domain("name", "in" if operator == "any" else "not in", names)
        if operator not in ("in", "not in"):
            _debug.logic(
                "linked_id_search_unsupported", model=self._name, operator=operator
            )
            return NotImplemented
        values = (
            list(value)
            if isinstance(value, Iterable) and not isinstance(value, str)
            else [value]
        )
        ids = [v for v in values if v]
        if any(not isinstance(v, int) for v in ids):
            _debug.logic(
                "linked_id_search_unsupported",
                model=self._name,
                operator=operator,
                reason="non_int_value",
            )
            return NotImplemented
        matched = Domain("name", "in", list(Module.browse(ids).exists().mapped("name")))
        if len(ids) < len(values):
            known = list(Module.search([]).mapped("name"))
            matched |= Domain("name", "not in", known)
        _debug.logic(
            "linked_id_search",
            model=self._name,
            operator=operator,
            ids=len(ids),
            with_unset=len(ids) < len(values),
        )
        return matched if operator == "in" else ~matched

    @api.depends("linked_id.state")
    def _compute_state(self) -> None:
        unknown = 0  # debuglog
        for link in self:
            link.state = link.linked_id.state or "unknown"
            unknown += not link.linked_id  # debuglog
        _debug.perf.count(
            "link_states_computed", model=self._name, links=len(self), unknown=unknown
        )
