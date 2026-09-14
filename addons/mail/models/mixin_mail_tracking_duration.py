import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

ROTTING_WINDOW_PARAM = "mail.rotting.max.months"
ROTTING_WINDOW_LEGACY_PARAM = "crm.lead.rot.max.months"
ROTTING_WINDOW_DEFAULT_MONTHS = 12


class MixinMailTrackingDuration(models.AbstractModel):
    _name = "mixin.mail.tracking.duration"
    _description = "Mixin to compute the time a record has spent in each value a many2one field can take"
    _inherit = ["mixin.mail.thread"]

    _track_duration_field = ""
    _track_duration_last_update_field = "date_last_stage_update"

    duration_tracking = fields.Json(
        string="Status time",
        compute="_compute_duration_tracking",
        help="JSON that maps ids from a many2one field to seconds spent",
    )
    rotting_days = fields.Integer(
        string="Days Rotting",
        compute="_compute_rotting",
        help="Days since the last update, counted only while the record is rotting",
    )
    is_rotting = fields.Boolean(
        string="Rotting",
        compute="_compute_rotting",
        search="_search_is_rotting",
    )

    def _get_track_duration_comodel(self) -> models.BaseModel | None:
        field = self._fields.get(self._track_duration_field)
        if field is None or field.type != "many2one":
            return None
        return self.env[field.comodel_name]

    def _get_duration_tracking_depends_fields(self) -> list[str]:
        return [self._track_duration_field] if self._track_duration_field else []

    def _get_rotting_depends_fields(self) -> list[str]:
        if not self._is_rotting_feature_enabled():
            return ["create_date"]
        return [
            self._track_duration_last_update_field,
            f"{self._track_duration_field}.rotting_threshold_days",
            "create_date",
        ]

    def _get_domain_rotting_records(self) -> Domain:
        return Domain(f"{self._track_duration_field}.rotting_threshold_days", ">", 0)

    def _is_rotting_feature_enabled(self) -> bool:
        comodel = self._get_track_duration_comodel()
        return (
            comodel is not None
            and "rotting_threshold_days" in comodel._fields
            and self._track_duration_last_update_field in self._fields
        )

    def _get_rotting_window_months(self) -> int:
        icp = self.env["ir.config_parameter"]
        months = icp._get_int_param(ROTTING_WINDOW_PARAM, -1)
        if months >= 0:
            return months
        return icp._get_int_param(
            ROTTING_WINDOW_LEGACY_PARAM, ROTTING_WINDOW_DEFAULT_MONTHS
        )

    def _get_rotting_window_start(self, now: datetime) -> datetime:
        return now - relativedelta(months=self._get_rotting_window_months())

    @api.depends(lambda self: self._get_duration_tracking_depends_fields())
    def _compute_duration_tracking(self) -> None:
        fname = self._track_duration_field
        field = self._fields.get(fname)
        if (
            field is None
            or field.type != "many2one"
            or fname not in self._track_get_fields()
        ):
            _logger.warning(
                "Field %r on model %r must be a tracked Many2one for duration "
                "tracking; leaving duration_tracking empty.",
                fname,
                self._name,
            )
            self.duration_tracking = False
            return

        field_id = self.env["ir.model.fields"]._get(self._name, fname).id

        trackings_by_res = defaultdict(list)
        if field_id and self.ids:
            self.env["mail.tracking.value"].flush_model(
                ["field_id", "mail_message_id", "old_value_integer"]
            )
            self.env["mail.message"].flush_model(["model", "res_id"])
            trackings = self.env.execute_query_dict(
                SQL(
                    """
                   SELECT m.res_id,
                          v.create_date,
                          v.old_value_integer
                     FROM mail_tracking_value v
                     JOIN mail_message m
                       ON m.id = v.mail_message_id
                    WHERE v.field_id = %(field_id)s
                      AND m.model = %(model_name)s
                      AND m.res_id IN %(record_ids)s
                 ORDER BY v.id
                """,
                    field_id=field_id,
                    model_name=self._name,
                    record_ids=tuple(self.ids),
                )
            )
            for tracking in trackings:
                trackings_by_res[tracking["res_id"]].append(tracking)
            _debug.perf.count(
                "duration_trackings_loaded",
                model=self._name,
                records=len(self),
                trackings=len(trackings),
            )

        for record in self:
            record.duration_tracking = record._get_duration_from_tracking(
                trackings_by_res[record._origin.id]
            )

    @api.depends(lambda self: self._get_rotting_depends_fields())
    def _compute_rotting(self) -> None:
        self.is_rotting = False
        self.rotting_days = 0
        if not self._is_rotting_feature_enabled():
            return

        now = self.env.cr.now()
        window_start = self._get_rotting_window_start(now)
        last_update_field = self._track_duration_last_update_field
        candidates = self.filtered_domain(self._get_domain_rotting_records())
        _debug.logic(
            "rotting_computed",
            model=self._name,
            records=len(self),
            candidates=len(candidates),
            window_start=window_start,
        )
        for stage, records in candidates.grouped(self._track_duration_field).items():
            threshold = timedelta(days=stage.rotting_threshold_days)
            for record in records:
                since = record[last_update_field] or record.create_date
                if since and window_start < since and since + threshold < now:
                    record.is_rotting = True
                    record.rotting_days = (now - since).days

    def _get_duration_from_tracking(self, trackings: list[dict]) -> dict:
        self.check_singleton()
        fname = self._track_duration_field
        now = self.env.cr.now()
        durations = defaultdict(int)
        previous_date = self.create_date or now

        pending = self.env.cr.precommit.data.get(f"mail.tracking.{self._name}", {}).get(
            self._origin.id
        )
        boundaries = list(trackings)
        if pending and (previous := pending.get(fname)) is not None:
            if previous.id and previous.id != self[fname].id:
                boundaries.append(
                    {"create_date": now, "old_value_integer": previous.id}
                )
        boundaries.append({"create_date": now, "old_value_integer": self[fname].id})

        for boundary in boundaries:
            durations[boundary["old_value_integer"]] += int(
                (boundary["create_date"] - previous_date).total_seconds()
            )
            previous_date = boundary["create_date"]

        return dict(durations)

    def _search_is_rotting(self, operator: str, value: Any) -> Domain:
        if not self._is_rotting_feature_enabled():
            raise UserError(
                self.env._("Model configuration does not support the rotting feature")
            )
        if operator not in ("in", "not in"):
            raise UserError(
                self.env._(
                    'For performance reasons, use "=" operators on rotting fields.'
                )
            )

        fname = self._track_duration_field
        stages = self._get_track_duration_comodel()
        last_update_field = self._track_duration_last_update_field

        self.flush_model(
            [fname, *(f for f in self._get_rotting_depends_fields() if "." not in f)]
        )
        stages.flush_model(["rotting_threshold_days"])

        query = self._search(self._get_domain_rotting_records())
        stage_alias = query.left_join(self._table, fname, stages._table, "id", fname)

        now = self.env.cr.now()
        sql_since = SQL(
            "COALESCE(%s, %s)",
            SQL.identifier(self._table, last_update_field),
            SQL.identifier(self._table, "create_date"),
        )
        query.add_where(SQL("%s > %s", sql_since, self._get_rotting_window_start(now)))
        query.add_where(
            SQL(
                "%s + %s * interval '1 day' < %s",
                sql_since,
                SQL.identifier(stage_alias, "rotting_threshold_days"),
                now,
            )
        )
        return Domain("id", "any" if operator == "in" else "not any", query)
