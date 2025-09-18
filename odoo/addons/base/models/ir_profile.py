import base64
import datetime
import json
import logging
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.http import request
from odoo.libs.constants import GC_UNLINK_LIMIT
from odoo.libs.profiling.speedscope import Speedscope
from odoo.tools.misc import str2bool
from odoo.tools.profiler import make_session

_logger = logging.getLogger(__name__)


class IrProfile(models.Model):
    _name = "ir.profile"
    _description = "Profiling results"
    _log_access = False  # avoid useless foreign key on res_user
    _order = "session desc, id desc"
    _allow_sudo_commands = False

    create_date = fields.Datetime("Creation Date")

    session = fields.Char("Session", index=True)
    name = fields.Char("Description")
    duration = fields.Float("Duration", digits=(9, 3), help="Real elapsed time")
    cpu_duration = fields.Float(
        "CPU Duration",
        digits=(9, 3),
        help="CPU clock (not including other processes or SQL)",
    )

    init_stack_trace = fields.Text("Initial stack trace", prefetch=False)

    sql = fields.Text("Sql", prefetch=False)
    sql_count = fields.Integer("Queries Count")
    traces_async = fields.Text("Traces Async", prefetch=False)
    traces_sync = fields.Text("Traces Sync", prefetch=False)
    others = fields.Text("others", prefetch=False)
    qweb = fields.Text("Qweb", prefetch=False)
    entry_count = fields.Integer("Entry count")

    speedscope = fields.Binary("Speedscope", compute="_compute_speedscope")
    speedscope_url = fields.Text("Open", compute="_compute_speedscope_url")

    config_url = fields.Text("Open profiles config", compute="_compute_config_url")

    @api.autovacuum
    def _gc_profile(self) -> tuple[int, bool]:
        # remove profiles older than 30 days
        domain = [
            (
                "create_date",
                "<",
                fields.Datetime.now() - datetime.timedelta(days=30),
            )
        ]
        records = self.sudo().search(domain, limit=GC_UNLINK_LIMIT)
        records.unlink()
        return len(records), len(records) == GC_UNLINK_LIMIT  # done, remaining

    def _compute_has_memory(self) -> bool:
        return all(
            bool(profile.others and json.loads(profile.others).get("memory"))
            for profile in self
        )

    def _generate_memory_profile(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        memory_graph = []
        memory_limit = params.get("memory_limit", 0)
        for profile in self:
            if profile.others:
                memory = json.loads(profile.others).get("memory", "[{}]")
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
        # The params variable is done to control input from the user
        # When expanding this, it should be select from an enum to input only the correct values
        params = self._parse_params(self.env.context)
        for execution in self:
            execution.speedscope = base64.b64encode(
                execution._generate_speedscope(params)
            )

    def _default_profile_params(self) -> dict[str, bool]:
        has_sql = any(profile.sql for profile in self)
        has_traces = any(profile.traces_async for profile in self)
        return {
            "combined_profile": has_sql and has_traces,
            "sql_no_gap_profile": has_sql and not has_traces,
            "sql_density_profile": False,
            "frames_profile": has_traces and not has_sql,
        }

    def _parse_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "constant_time": str2bool(params.get("constant_time", False)),
            "aggregate_sql": str2bool(params.get("aggregate_sql", False)),
            "use_context": str2bool(params.get("use_execution_context", True)),
            "combined_profile": str2bool(params.get("combined_profile", False)),
            "sql_no_gap_profile": str2bool(params.get("sql_no_gap_profile", False)),
            "sql_density_profile": str2bool(params.get("sql_density_profile", False)),
            "frames_profile": str2bool(params.get("frames_profile", False)),
            "profile_aggregation_mode": params.get("profile_aggregation_mode", "tabs"),
            "memory_limit": int(params.get("memory_limit", 0)),
        }

    def _generate_speedscope(self, params: dict[str, Any]) -> bytes:
        init_stack_trace = self[0].init_stack_trace
        if not init_stack_trace:
            return b"{}"
        for record in self:
            if record.init_stack_trace != init_stack_trace:
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

        result = json.dumps(sp.make(**params))
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

    @api.depends("speedscope")
    def _compute_speedscope_url(self) -> None:
        for profile in self:
            profile.speedscope_url = f"/web/speedscope/{profile.id}"

    def _enabled_until(self) -> str | None:
        """
        If the profiling is enabled, return until when it is enabled.
        Otherwise return ``None``.
        """
        limit = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("base.profiling_enabled_until", "")
        )
        limit_dt = fields.Datetime.from_string(limit)
        return limit if limit_dt and fields.Datetime.now() < limit_dt else None

    @api.model
    def set_profiling(
        self,
        profile: bool | None = None,
        collectors: list[str] | None = None,
        params: dict | None = None,
    ) -> dict[str, Any]:
        """
        Enable or disable profiling for the current user.

        :param profile: ``True`` to enable profiling, ``False`` to disable it.
        :param list[str] | None collectors: optional list of collectors to use (string)
        :param dict | None params: optional parameters set on the profiler object
        """
        # Note: parameters are coming from a rpc calls or route param (public user),
        # meaning that corresponding session variables are client-defined.
        # This allows to activate any profiler, but can be
        # dangerous handling request.session.profile_collectors/profile_params.
        if not request:
            raise UserError(
                self.env._("Profiling can only be toggled from an HTTP request.")
            )
        if profile:
            limit = self._enabled_until()
            _logger.info("User %s started profiling", self.env.user.name)
            if not limit:
                request.session["profile_session"] = None
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
                request.session["profile_session"] = make_session(self.env.user.name)
                request.session["profile_expiration"] = limit
                if request.session.get("profile_collectors") is None:
                    request.session["profile_collectors"] = []
                if request.session.get("profile_params") is None:
                    request.session["profile_params"] = {}
        elif profile is not None:
            request.session["profile_session"] = None

        if collectors is not None:
            request.session["profile_collectors"] = collectors

        if params is not None:
            request.session["profile_params"] = params

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
        [
            ("minutes_5", "5 Minutes"),
            ("hours_1", "1 Hour"),
            ("days_1", "1 Day"),
            ("months_1", "1 Month"),
        ],
        string="Enable profiling for",
    )
    expiration = fields.Datetime(
        "Enable profiling until",
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
        self.env["ir.config_parameter"].set_param(
            "base.profiling_enabled_until", self.expiration
        )
        return False
