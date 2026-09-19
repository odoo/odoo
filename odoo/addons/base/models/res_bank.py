from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ResBank(models.Model):
    _name = "res.bank"
    _description = "Bank"
    _order = "name, id"
    _rec_names_search = ["name", "bic"]

    name = fields.Char(required=True)
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char()
    city = fields.Char()
    state = fields.Many2one(
        comodel_name="res.country.state",
        string="Fed. State",
        domain="[('country_id', '=?', country)]",
    )
    country = fields.Many2one(comodel_name="res.country")
    country_code = fields.Char(
        related="country.code",
        string="Country Code",
    )
    email = fields.Char()
    phone_ids = fields.Many2many(
        comodel_name="phone.number",
        relation="res_bank_phone_number_rel",
        column1="bank_id",
        column2="phone_number_id",
        string="Phone Numbers",
    )
    active = fields.Boolean(default=True)
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
        _debug.lifecycle("bank_create", count=len(vals_list))
        return super().create([self._normalize_vals(vals) for vals in vals_list])

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("bank_write", count=len(self), fields=list(vals))
        return super().write(self._normalize_vals(vals))

    @api.onchange("country")
    def _onchange_country(self) -> None:
        if self.country and self.country != self.state.country_id:
            _debug.logic(
                "state_cleared_on_country_change",
                country=self.country.id,
                state=self.state.id,
            )
            self.state = False

    @api.onchange("state")
    def _onchange_state(self) -> None:
        if self.state.country_id:
            self.country = self.state.country_id
