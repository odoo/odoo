from typing import Any

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools.safe_eval import safe_eval

from .ir_actions_actions import WINDOW_TARGETS

_debug = DebugLog(__name__)


class IrActionsClient(models.Model):
    _name = "ir.actions.client"
    _description = "Client Action"
    _inherit = ["ir.actions.actions"]
    _table = "ir_act_client"

    tag = fields.Char(
        string="Client action tag",
        required=True,
        help="An arbitrary string, interpreted by the client"
        " according to its own needs and wishes. There "
        "is no central tag repository across clients.",
    )
    target = fields.Selection(
        selection=WINDOW_TARGETS,
        string="Target Window",
        default="current",
    )
    res_model = fields.Char(
        string="Destination Model",
        help="Optional model, mostly used for needactions.",
    )
    context = fields.Char(
        string="Context Value",
        default="{}",
        required=True,
        help="Context dictionary as Python expression, empty by default (Default: {})",
    )
    params = fields.Binary(
        string="Supplementary arguments",
        compute="_compute_params",
        inverse="_inverse_params",
        help="Arguments sent to the client along with the view tag",
    )
    params_store = fields.Binary(
        string="Params storage",
        attachment=False,
        readonly=True,
    )

    @api.depends("params_store")
    @api.depends_context("uid")
    def _compute_params(self) -> None:
        self_bin = self.with_context(bin_size=False, bin_size_params_store=False)
        for record, record_bin in zip(self, self_bin, strict=True):
            stored = record_bin.params_store
            if not stored:
                _debug.logic("params_empty", action=record.id)
                record.params = stored
                continue
            params = self._parse_params(stored)
            if isinstance(params, dict):
                _debug.logic("params_evaluated", action=record.id, keys=len(params))
                record.params = params
            else:
                _debug.logic("params_unparsable", action=record.id)
                record.params = False

    def _inverse_params(self) -> None:
        for record in self:
            params = record.params
            if isinstance(params, bytes | str):
                params = self._parse_params(params)
            if not params:
                record.params_store = False
            elif isinstance(params, dict):
                record.params_store = repr(params)
                _debug.lifecycle("params_stored", action=record.id, keys=len(params))
            else:
                _debug.logic(
                    "params_rejected", action=record.id, type=type(params).__name__
                )
                raise ValidationError(
                    self.env._(
                        "The parameters of client action '%(name)s' must be a "
                        "dictionary, not %(type)s.",
                        name=record.name,
                        type=type(params).__name__,
                    )
                )

    @api.model
    def _parse_params(self, source: bytes | str) -> Any:
        if isinstance(source, bytes):
            source = source.decode()
        try:
            return safe_eval(source, {"uid": self.env.uid})
        except Exception as exc:
            _debug.logic("params_kept_as_source", error=type(exc).__name__)
            return source

    def _get_field_target_model(self) -> str:
        return "res_model"

    def _get_fields_binding_extra(self) -> tuple[str, ...]:
        return ("res_model",)

    def _get_fields_readable(self) -> frozenset[str]:
        return super()._get_fields_readable() | {
            "context",
            "params",
            "res_model",
            "tag",
            "target",
        }
