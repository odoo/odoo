import logging

from odoo import SUPERUSER_ID, Command, api
from odoo.db.schema import column_exists
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version or not column_exists(
        cr, "maintenance_order", "recurring_maintenance"
    ):
        return
    # date_recurrence_origin exists only on databases upgraded between feadf2864ac1
    # and this migration; everywhere else a series starts on its request's date.
    origin = (
        SQL("request.date_recurrence_origin")
        if column_exists(cr, "maintenance_order", "date_recurrence_origin")
        else SQL("NULL::timestamp")
    )
    cr.execute(
        SQL(
            """
            SELECT request.id,
                   request.repeat_interval,
                   request.repeat_unit,
                   request.repeat_type,
                   request.repeat_until,
                   COALESCE(%s, request.date_scheduled_start, request.create_date)
              FROM maintenance_order request
         LEFT JOIN maintenance_stage stage ON stage.id = request.stage_id
             WHERE request.recurring_maintenance
               AND NOT COALESCE(request.archive, FALSE)
               AND NOT COALESCE(stage.done, FALSE)
          ORDER BY request.id
            """,
            origin,
        )
    )
    env = api.Environment(cr, SUPERUSER_ID, {"tracking_disable": True})
    series = {}
    for request_id, interval, unit, repeat_type, until, start in cr.fetchall():
        request = env["maintenance.order"].browse(request_id)
        key = (
            request.name,
            request.equipment_id.id,
            request.company_id.id,
            interval,
            unit,
            repeat_type,
            until,
        )
        series.setdefault(key, []).append((request, start))
    for (
        _name,
        _equipment,
        _company,
        interval,
        unit,
        repeat_type,
        until,
    ), members in series.items():
        request, start = members[0]
        # An "until" series without its end date produced no successor: keep it
        # stopped rather than let it run for ever.
        stopped = repeat_type == "until" and not until
        try:
            with cr.savepoint():
                env["maintenance.plan"].create(
                    {
                        "name": request.name,
                        "active": not stopped,
                        "company_id": request.company_id.id,
                        "equipment_id": request.equipment_id.id,
                        "maintenance_team_id": request.maintenance_team_id.id,
                        "user_id": request.user_id.id,
                        "duration": request.duration,
                        "priority": request.priority,
                        "description": request.description,
                        "repeat_interval": interval or 1,
                        "repeat_unit": unit or "week",
                        "repeat_type": "until"
                        if repeat_type == "until" and until
                        else "forever",
                        "repeat_until": until,
                        "repeat_anchor": "fixed",
                        "date_first_occurrence": start,
                        "order_ids": [
                            Command.link(member.id) for member, _start in members
                        ],
                    }
                )
        except Exception:
            _logger.exception(
                "maintenance 1.2: series of request %s could not become a plan",
                request.id,
            )
