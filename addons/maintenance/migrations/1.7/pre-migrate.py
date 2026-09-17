from odoo.tools.module_data import rename_field, rename_in_stored_expressions

RENAMED_FIELDS = (
    ("maintenance.order", "date_order", "date_confirmed"),
    ("maintenance.order", "close_date", "date_done"),
    ("maintenance.order", "schedule_date", "date_scheduled_start"),
    ("maintenance.order", "schedule_end", "date_scheduled_end"),
    ("maintenance.plan", "date_start", "date_first_occurrence"),
    ("maintenance.order", "date_occurrence", "date_plan_slot"),
    ("maintenance.plan", "date_next", "date_next_scheduled"),
    ("resource.resource", "date_effective", "date_in_service"),
    ("resource.resource", "latest_failure_date", "date_last_failure"),
    ("resource.resource", "estimated_next_failure", "date_next_failure"),
    ("resource.asset", "date_effective", "date_in_service"),
    ("resource.asset", "latest_failure_date", "date_last_failure"),
    ("resource.asset", "estimated_next_failure", "date_next_failure"),
    (
        "team.team",
        "maintenance_todo_order_count_date",
        "maintenance_todo_order_count_scheduled",
    ),
)


def migrate(cr, version):
    if not version:
        return
    for model, old, new in RENAMED_FIELDS:
        rename_field(cr, model, old, new)
        rename_in_stored_expressions(cr, old, new, model=model)
    # The requester is whoever created the order; saved filters, rules and views
    # that read the dropped field read the creator instead.
    rename_in_stored_expressions(
        cr, "owner_user_id", "create_uid", model="maintenance.order"
    )
