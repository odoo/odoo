from odoo.addons.team.tools.fold import fold_team_model


def migrate(cr, version):
    if not version:
        return
    fold_team_model(
        cr,
        "maintenance.team",
        "use_maintenance",
        members=("maintenance_team_users_rel", "res_users_id", "maintenance_team_id"),
        alias_usage="maintenance",
        alias_team_field="maintenance_team_id",
        links=("maintenance_team_id",),
        renamed={
            "request_ids": "maintenance_request_ids",
            "equipment_ids": "maintenance_equipment_ids",
            "todo_request_count": "maintenance_todo_request_count",
            "todo_request_count_date": "maintenance_todo_request_count_date",
            "todo_request_count_high_priority": "maintenance_todo_request_count_high_priority",
            "todo_request_count_block": "maintenance_todo_request_count_block",
            "todo_request_count_unscheduled": "maintenance_todo_request_count_unscheduled",
        },
    )
