from odoo.db.schema import column_exists, table_exists
from odoo.tools.module_data import rename_field, rename_model

RENAMED_XMLIDS = {
    "hr_equipment_request_view_search": "maintenance_order_view_search",
    "maintenance_request_view_activity": "maintenance_order_view_activity",
    "hr_equipment_request_view_form": "maintenance_order_view_form",
    "hr_equipment_request_view_kanban": "maintenance_order_view_kanban",
    "hr_equipment_request_view_tree": "maintenance_order_view_list",
    "hr_equipment_request_view_graph": "maintenance_order_view_graph",
    "hr_equipment_request_view_pivot": "maintenance_order_view_pivot",
    "hr_equipment_view_calendar": "maintenance_order_view_calendar",
    "hr_equipment_request_action": "maintenance_order_action",
    "hr_equipment_request_action_link": "maintenance_order_action_link",
    "hr_equipment_request_action_from_equipment": "maintenance_order_action_from_equipment",
    "hr_equipment_todo_request_action_from_dashboard": "maintenance_order_action_from_dashboard",
    "hr_equipment_request_action_cal": "maintenance_order_action_cal",
    "maintenance_request_action_reports": "maintenance_order_action_reports",
    "menu_m_request": "menu_m_order",
    "menu_m_request_form": "menu_m_order_form",
    "menu_m_request_calendar": "menu_m_order_calendar",
    "maintenance_request_reporting": "maintenance_order_reporting",
    "equipment_request_rule_user": "maintenance_order_rule_user",
    "equipment_request_rule_admin_user": "maintenance_order_rule_admin_user",
    "maintenance_request_comp_rule": "maintenance_order_comp_rule",
    "mail_act_maintenance_request": "mail_act_maintenance_order",
    "mt_req_created": "mt_order_created",
    "mt_req_status": "mt_order_state",
    "mt_cat_req_created": "mt_cat_order_created",
    "access_maintenance_system_user": "access_maintenance_order_user",
    "m_request_3": "m_order_3",
    "m_request_4": "m_order_4",
    "m_request_6": "m_order_6",
    "m_request_7": "m_order_7",
    "m_request_8": "m_order_8",
}

RENAMED_FIELDS = (
    ("maintenance.order", "request_date", "date_order"),
    ("maintenance.plan", "request_ids", "order_ids"),
    ("maintenance.plan", "request_count", "order_count"),
    ("team.team", "maintenance_request_ids", "maintenance_order_ids"),
    ("team.team", "maintenance_todo_request_count", "maintenance_todo_order_count"),
    (
        "team.team",
        "maintenance_todo_request_count_date",
        "maintenance_todo_order_count_date",
    ),
    (
        "team.team",
        "maintenance_todo_request_count_high_priority",
        "maintenance_todo_order_count_high_priority",
    ),
    (
        "team.team",
        "maintenance_todo_request_count_block",
        "maintenance_todo_order_count_block",
    ),
    (
        "team.team",
        "maintenance_todo_request_count_unscheduled",
        "maintenance_todo_order_count_unscheduled",
    ),
)

DEFAULT_STAGES = ("stage_0", "stage_1", "stage_3", "stage_4")


def migrate(cr, version):
    if not version:
        return
    if table_exists(cr, "maintenance_request"):
        rename_model(cr, "maintenance.request", "maintenance.order")
    for old, new in RENAMED_XMLIDS.items():
        cr.execute(
            """
            UPDATE ir_model_data
               SET name = %s
             WHERE module = 'maintenance' AND name = %s
               AND NOT EXISTS (
                   SELECT 1 FROM ir_model_data
                    WHERE module = 'maintenance' AND name = %s
               )
            """,
            (new, old, new),
        )
    for model, old, new in RENAMED_FIELDS:
        rename_field(cr, model, old, new)
    _migrate_stages_to_state(cr)


def _migrate_stages_to_state(cr):
    if column_exists(cr, "maintenance_order", "state") or not column_exists(
        cr, "maintenance_order", "stage_id"
    ):
        return
    cr.execute("ALTER TABLE maintenance_order ADD COLUMN state varchar")
    cr.execute(
        """
        WITH first_open AS (
            SELECT id FROM maintenance_stage
             WHERE NOT COALESCE(done, FALSE)
          ORDER BY sequence, id
             LIMIT 1
        )
        UPDATE maintenance_order o
           SET state = CASE
                   WHEN COALESCE(stage.done, FALSE) THEN 'done'
                   WHEN COALESCE(o.archive, FALSE) THEN 'cancel'
                   WHEN o.stage_id IS NULL
                     OR o.stage_id = (SELECT id FROM first_open) THEN 'confirmed'
                   ELSE 'in_progress'
               END
          FROM maintenance_order o2
     LEFT JOIN maintenance_stage stage ON stage.id = o2.stage_id
         WHERE o2.id = o.id
        """
    )
    cr.execute(
        """
        UPDATE maintenance_order
           SET kanban_state = 'normal'
         WHERE kanban_state = 'done' AND state IN ('done', 'cancel')
        """
    )
    cr.execute(
        """
        CREATE TABLE maintenance_order_migrated_stage AS
        SELECT o.id AS order_id, stage.name AS stage_name
          FROM maintenance_order o
          JOIN maintenance_stage stage ON stage.id = o.stage_id
         WHERE NOT EXISTS (
               SELECT 1 FROM ir_model_data d
                WHERE d.module = 'maintenance'
                  AND d.model = 'maintenance.stage'
                  AND d.res_id = stage.id
                  AND d.name = ANY(%s)
         )
        """,
        (list(DEFAULT_STAGES),),
    )
