import logging
from typing import Any, Self

from odoo import api, fields, models, tools
from odoo.api import ValuesType
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class DecimalPrecision(models.Model):
    _name = "decimal.precision"
    _description = "Decimal Precision"

    name = fields.Char(
        string="Usage",
        required=True,
    )
    digits = fields.Integer(
        default=2,
        required=True,
    )

    _name_uniq = models.Constraint(
        "unique (name)",
        "Only one value can be defined for each given usage!",
    )

    @api.constrains("digits")
    def _check_digits(self) -> None:
        if any(record.digits < 0 for record in self):
            _debug.logic("digits_rejected", names=self.mapped("name"))
            raise ValidationError(
                self.env._("The number of digits cannot be negative.")
            )

    @api.model
    @tools.ormcache("application", cache="stable")
    def get_precision(self, application: str) -> int:
        precision = self.sudo().search_fetch(
            [("name", "=", application)], ["digits"], limit=1
        )
        _debug.perf.count(
            "precision_computed",
            application=application,
            digits=precision.digits if precision else None,
        )
        if not precision:
            _logger.warning(
                "Decimal precision '%s' is not defined, using the default of 2 digits",
                application,
            )
            return 2
        return precision.digits

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        res = super().create(vals_list)
        _debug.lifecycle("create", names=res.mapped("name"))
        self.env.registry.clear_cache("stable")
        return res

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("write", names=self.mapped("name"), fields=list(vals))
        res = super().write(vals)
        self.env.registry.clear_cache("stable")
        return res

    def unlink(self) -> bool:
        _debug.lifecycle("unlink", names=self.mapped("name"))
        res = super().unlink()
        self.env.registry.clear_cache("stable")
        return res

    @api.onchange("digits")
    def _onchange_digits(self) -> dict[str, Any] | None:
        if self.digits < self._origin.digits:
            _debug.logic(
                "digits_reduced",
                name=self.name,
                old=self._origin.digits,
                new=self.digits,
            )
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
