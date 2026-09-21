from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog
from odoo.tools import ormcache

_debug = DebugLog(__name__)


class ResBank(models.Model):
    _name = "res.bank"
    _description = "Bank"
    _inherits = {"res.partner": "partner_id"}
    _order = "name, id"
    _rec_names_search = ["name", "bic"]
    _inherits_rules = False
    _inherits_sudo_fields = (
        "name",
        "email",
        "phone_ids",
        "street",
        "street2",
        "zip",
        "city",
        "state_id",
        "country_id",
        "country_code",
        "active",
    )

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Party",
        index=True,
        required=True,
        ondelete="restrict",
    )
    bic = fields.Char(
        string="Bank Identifier Code",
        index=True,
        help="Sometimes called BIC or Swift.",
    )

    @api.depends("name", "bic")
    def _compute_display_name(self) -> None:
        for bank in self:
            name = (bank.name or "") + ((bank.bic and (" - " + bank.bic)) or "")
            bank.display_name = name

    @api.model
    def _search_display_name(self, operator: str, value: str) -> list:
        if operator in ("ilike", "not ilike") and value:
            domain = [
                "|",
                ("bic", "=ilike", value + "%"),
                ("name", "ilike", value),
            ]
            if operator == "not ilike":
                domain = ["!", *domain]
            _debug.logic("bank_name_search", operator=operator, by="bic_or_name")
            return domain
        return super()._search_display_name(operator, value)

    def _normalize_vals(self, vals: ValuesType) -> ValuesType:
        if bic := vals.get("bic"):
            return {**vals, "bic": bic.upper()}
        return vals

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        vals_list = [self._normalize_vals(vals) for vals in vals_list]
        for vals in vals_list:
            if not vals.get("partner_id"):
                vals.setdefault("is_company", True)
        _debug.lifecycle("bank_create", count=len(vals_list))
        banks = super().create(vals_list)
        self.env.registry.clear_cache()
        return banks

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("bank_write", count=len(self), fields=list(vals))
        res = super().write(self._normalize_vals(vals))
        if "partner_id" in vals:
            self.env.registry.clear_cache()
        return res

    def unlink(self) -> bool:
        _debug.lifecycle("bank_unlink", count=len(self))
        res = super().unlink()
        self.env.registry.clear_cache()
        return res

    @ormcache()
    def _get_bank_partner_ids(self) -> tuple[int, ...]:
        partner_ids = tuple(
            self.env["res.bank"]
            .sudo()
            .with_context(active_test=False)
            .search([])
            .partner_id.ids
        )
        _debug.perf.count("bank_partner_ids_computed", partners=len(partner_ids))
        return partner_ids
