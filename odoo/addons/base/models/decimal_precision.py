import logging
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.orm._typing import ValuesType

_logger = logging.getLogger(__name__)


class DecimalPrecision(models.Model):
    _name = "decimal.precision"
    _description = "Decimal Precision"

    name = fields.Char("Usage", required=True)
    digits = fields.Integer("Digits", required=True, default=2)

    _name_uniq = models.Constraint(
        "unique (name)",
        "Only one value can be defined for each given usage!",
    )

    @api.model
    @tools.ormcache("application", cache="stable")
    def precision_get(self, application: str) -> int:
        self.flush_model(["name", "digits"])
        self.env.cr.execute(
            "select digits from decimal_precision where name=%s", (application,)
        )
        res = self.env.cr.fetchone()
        return res[0] if res else 2

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        self.env.registry.clear_cache("stable")
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        res = super().write(vals)
        self.env.registry.clear_cache("stable")
        return res

    def unlink(self) -> bool:
        res = super().unlink()
        self.env.registry.clear_cache("stable")
        return res

    @api.onchange("digits")
    def _onchange_digits_warning(self) -> dict[str, Any] | None:
        if self.digits < self._origin.digits:
            return {
                "warning": {
                    "title": self.env._("Warning for %s", self.name),
                    "message": self.env._(
                        "The precision has been reduced for %s.\n"
                        "Note that existing data WON'T be updated by this change.\n\n"
                        "As decimal precisions impact the whole system, this may cause critical issues.\n"
                        "E.g. reducing the precision could disturb your financial balance.\n\n"
                        "Therefore, changing decimal precisions in a running database is not recommended.",
                        self.name,
                    ),
                }
            }
        return None
