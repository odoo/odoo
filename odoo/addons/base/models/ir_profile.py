import base64
import datetime
import json
import logging
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.profiling import Speedscope
from odoo.models import GC_UNLINK_LIMIT
from odoo.tools.misc import str2bool
from odoo.tools.profiler import get_session_name

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrProfile(models.Model):
    _name = "ir.profile"
    _description = "Profiling results"
    _log_access = False
    _order = "session desc, id desc"
    _allow_sudo_commands = False

    create_date = fields.Datetime(string="Creation Date")

    session = fields.Char(index=True)
    name = fields.Char(string="Description")
    duration = fields.Float(
        digits=(9, 3),
        help="Real elapsed time",
    )
    cpu_duration = fields.Float(
        string="CPU Duration",
        digits=(9, 3),
        help="CPU clock (not including other processes or SQL)",
    )

    init_stack_trace = fields.Text(
        string="Initial stack trace",
        prefetch=False,
    )

    sql = fields.Text(prefetch=False)
    sql_count = fields.Integer(string="Queries Count")
    traces_async = fields.Text(prefetch=False)
    traces_sync = fields.Text(prefetch=False)
    others = fields.Text(
        string="others",
        prefetch=False,
    )
    qweb = fields.Text(prefetch=False)
    entry_count = fields.Integer(string="Entry count")

    speedscope = fields.Binary(compute="_compute_speedscope")
    speedscope_url = fields.Text(
        string="Open",
        compute="_compute_speedscope_url",
    )

    config_url = fields.Text(
        string="Open profiles config",
        compute="_compute_config_url",
    )

    @api.autovacuum
    def _gc_profile(self) -> tuple[int, bool]:
        domain = [
            (
                "create_date",
                "<",
                fields.Datetime.now() - datetime.timedelta(days=30),
            )
        ]
        records = self.sudo().search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        _debug.lifecycle("gc_profile", count=len(records))
        return len(records), len(records) == GC_UNLINK_LIMIT

    def _has_memory(self) -> bool:
        return all(
            bool(profile.others and json.loads(profile.others).get("memory"))
            for profile in self
        )

    def _generate_memory_profile(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        self.check_access("read")
        memory_graph = []
        memory_limit = params.get("memory_limit", 0)
        _debug.pipeline("memory_profile", profiles=len(self), memory_limit=memory_limit)
        for profile in self:
            if profile.others:
                memory = json.loads(profile.others).get("memory", "[]")
                memory_tracebacks = json.loads(memory)[:-1]
                memory_graph.extend(
                    {
                        "samples": [
                            sample
                            for sample in entry["memory_tracebacks"]
                            if sample.get("size", 0) >= memory_limit
                        ],
                        "start": entry["start"],
                    }
                    for entry in memory_tracebacks
                )
        return memory_graph

    def _compute_config_url(self) -> None:
        for profile in self:
            profile.config_url = f"/web/profile_config/{profile.id}"

    @api.depends("init_stack_trace")
    def _compute_speedscope(self) -> None:
        params = self._parse_params(self.env.context)
        for execution in self:
            execution.speedscope = base64.b64encode(
                execution._generate_speedscope(params)
            )

    def _prepare_profile_params_default(self) -> dict[str, bool]:
        has_sql = any(profile.sql for profile in self)
        has_traces = any(profile.traces_async for profile in self)
        _debug.logic(
            "profile_defaults", profiles=len(self), sql=has_sql, traces=has_traces
        )
        return {
            "combined_profile": has_sql and has_traces,
            "sql_no_gap_profile": has_sql and not has_traces,
            "sql_density_profile": False,
            "frames_profile": has_traces and not has_sql,
        }

    def _parse_params(self, params: dict[str, Any]) -> dict[str, Any]:
        aggregation_mode = params.get("profile_aggregation_mode")
        if aggregation_mode not in ("tabs", "temporal"):
            aggregation_mode = "tabs"
        _debug.logic(
            "profile_params_parsed", keys=sorted(params), aggregation=aggregation_mode
        )
        return {
            "constant_time": str2bool(
                params.get("constant_time", False), default=False
            ),
            "aggregate_sql": str2bool(
                params.get("aggregate_sql", False), default=False
            ),
            "use_context": str2bool(
                params.get("use_execution_context", True), default=True
            ),
            "combined_profile": str2bool(
                params.get("combined_profile", False), default=False
            ),
            "sql_no_gap_profile": str2bool(
                params.get("sql_no_gap_profile", False), default=False
            ),
            "sql_density_profile": str2bool(
                params.get("sql_density_profile", False), default=False
            ),
            "frames_profile": str2bool(
                params.get("frames_profile", False), default=False
            ),
            "profile_aggregation_mode": aggregation_mode,
            "memory_limit": self._parse_memory_limit(params.get("memory_limit")),
        }

    @staticmethod
    def _parse_memory_limit(value: Any) -> int:
        try:
            return int(value or 0)
        except TypeError, ValueError:
            return 0

    def _generate_speedscope(self, params: dict[str, Any]) -> bytes:
        self.check_access("read")
        init_stack_trace = self[0].init_stack_trace
        if not init_stack_trace:
            _debug.logic("speedscope_empty", profiles=self.ids)
            return b"{}"
        for record in self:
            if record.init_stack_trace != init_stack_trace:
                _debug.logic(
                    "speedscope_refused", reason="stack_mismatch", profiles=self.ids
                )
                raise UserError(
                    self.env._(
                        "All profiles must have the same initial stack trace to be displayed together."
                    )
                )
        sp = Speedscope(init_stack_trace=json.loads(init_stack_trace))
        for profile in self:
            if (
                params["sql_no_gap_profile"]
                or params["sql_density_profile"]
                or params["combined_profile"]
            ) and profile.sql:
                sp.add(f"sql {profile.id}", json.loads(profile.sql))
            if (
                params["frames_profile"] or params["combined_profile"]
            ) and profile.traces_async:
                sp.add(f"frames {profile.id}", json.loads(profile.traces_async))
            if params["profile_aggregation_mode"] == "tabs":
                profile._add_outputs(
                    sp,
                    f"{profile.id} {profile.name}" if len(self) > 1 else "",
                    params,
                )

        if params["profile_aggregation_mode"] == "temporal":
            self._add_outputs(sp, "all", params)

        with _debug.perf("speedscope_document", profiles=len(self)) as span:
            result = json.dumps(sp.prepare_document(**params))
            span.set(bytes=len(result))
        return result.encode("utf-8")

    def _add_outputs(self, sp: Speedscope, suffix: str, params: dict[str, Any]) -> None:
        sql = [f"sql {profile.id}" for profile in self]
        frames = [f"frames {profile.id}" for profile in self]
        if params["combined_profile"]:
            sp.add_output(sql + frames, display_name=f"Combined {suffix}", **params)
        if params["sql_no_gap_profile"]:
            sp.add_output(
                sql,
                hide_gaps=True,
                display_name=f"Sql (no gap) {suffix}",
                **params,
            )
        if params["sql_density_profile"]:
            sp.add_output(
                sql,
                continuous=False,
                complete=False,
                display_name=f"Sql (density) {suffix}",
                **params,
            )
        if params["frames_profile"]:
            sp.add_output(frames, display_name=f"Frames {suffix}", **params)

    def _compute_speedscope_url(self) -> None:
        for profile in self:
            profile.speedscope_url = f"/web/speedscope/{profile.id}"

    def _get_enabled_until(self) -> str | None:
        limit = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("base.profiling_enabled_until", "")
        )
        limit_dt = fields.Datetime.from_string(limit)
        enabled = bool(limit_dt and fields.Datetime.now() < limit_dt)
        _debug.logic("profiling_window", enabled=enabled, until=limit or None)
        return limit if enabled else None

    @api.model
    def set_profiling(
        self,
        profile: bool | None = None,
        collectors: list[str] | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        if not request:
            _debug.logic("profiling_refused", reason="no_request")
            raise UserError(
                self.env._("Profiling can only be toggled from an HTTP request.")
            )
        if profile:
            limit = self._get_enabled_until()
            _logger.info("User %s started profiling", self.env.user.name)
            if not limit:
                request.session["profile_session"] = None
                _debug.logic(
                    "profiling_not_enabled",
                    uid=self.env.uid,
                    system=self.env.user._is_system(),
                )
                if self.env.user._is_system():
                    return {
                        "type": "ir.actions.act_window",
                        "view_mode": "form",
                        "res_model": "base.enable.profiling.wizard",
                        "target": "new",
                        "views": [[False, "form"]],
                    }
                raise UserError(
                    self.env._(
                        "Profiling is not enabled on this database. Please contact an administrator."
                    )
                )
            if not request.session.get("profile_session"):
                _debug.lifecycle("profile_session_opened", uid=self.env.uid)
                request.session["profile_session"] = get_session_name(
                    self.env.user.name
                )
                request.session["profile_expiration"] = limit
                if request.session.get("profile_collectors") is None:
                    request.session["profile_collectors"] = []
                if request.session.get("profile_params") is None:
                    request.session["profile_params"] = {}
        elif profile is not None:
            _debug.lifecycle("profile_session_closed", uid=self.env.uid)
            request.session["profile_session"] = None

        if collectors is not None:
            request.session["profile_collectors"] = collectors

        if params is not None:
            request.session["profile_params"] = params

        _debug.lifecycle(
            "profiling_toggled",
            uid=self.env.uid,
            profile=profile,
            session=request.session.get("profile_session"),
            collectors=request.session.get("profile_collectors"),
        )
        return {
            "session": request.session.get("profile_session"),
            "collectors": request.session.get("profile_collectors"),
            "params": request.session.get("profile_params"),
        }

    def action_view_speedscope(self) -> dict[str, str]:
        ids = ",".join(str(p.id) for p in self)
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/profile_config/{ids}",
            "target": "new",
        }


class BaseEnableProfilingWizard(models.TransientModel):
    _name = "base.enable.profiling.wizard"
    _description = "Enable profiling for some time"

    duration = fields.Selection(
        selection=[
            ("minutes_5", "5 Minutes"),
            ("hours_1", "1 Hour"),
            ("days_1", "1 Day"),
            ("months_1", "1 Month"),
        ],
        string="Enable profiling for",
    )
    expiration = fields.Datetime(
        string="Enable profiling until",
        compute="_compute_expiration",
        store=True,
        readonly=False,
    )

    @api.depends("duration")
    def _compute_expiration(self) -> None:
        for record in self:
            unit, quantity = (record.duration or "days_0").split("_")
            record.expiration = fields.Datetime.now() + relativedelta(
                **{unit: int(quantity)}
            )

    def submit(self) -> bool:
        _debug.lifecycle(
            "profiling_enabled_until", uid=self.env.uid, until=str(self.expiration)
        )
        self.env["ir.config_parameter"].set_param(
            "base.profiling_enabled_until", self.expiration
        )
        return False
