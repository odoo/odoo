from odoo import SUPERUSER_ID, Command, api
from odoo.db.schema import column_exists


def migrate(cr, version):
    if not version or not column_exists(
        cr, "maintenance_request", "recurring_maintenance"
    ):
        return
    cr.execute(
        """
        SELECT request.id,
               request.repeat_interval,
               request.repeat_unit,
               request.repeat_type,
               request.repeat_until,
               COALESCE(request.date_recurrence_origin, request.schedule_date, request.create_date)
          FROM maintenance_request request
          JOIN maintenance_stage stage ON stage.id = request.stage_id
         WHERE request.recurring_maintenance
           AND NOT COALESCE(request.archive, FALSE)
           AND NOT COALESCE(stage.done, FALSE)
        """
    )
    rows = cr.fetchall()
    env = api.Environment(cr, SUPERUSER_ID, {})
    requests = env["maintenance.request"].browse([row[0] for row in rows])
    env["maintenance.plan"].create(
        [
            {
                "name": request.name,
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
                "date_start": start,
                "request_ids": [Command.link(request.id)],
            }
            for request, (_id, interval, unit, repeat_type, until, start) in zip(
                requests, rows, strict=True
            )
        ]
    )
