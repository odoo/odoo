from odoo.db.schema import column_exists

FACTS = (
    "date_in_service",
    "maintenance_team_id",
    "technician_user_id",
    "expected_mtbf",
)
DROPPED = (*FACTS, "maintenance_count", "maintenance_open_count")


def migrate(cr, version):
    """The kernel's maintenance facts become a profile of the resource. A
    resource gets one when it holds a team, a technician or an expected
    MTBF, or has ever been maintained or planned; the dates alone were a
    default every resource carried. The columns then leave the kernel, which
    the ORM never does on its own."""
    if not all(column_exists(cr, "resource_resource", column) for column in FACTS):
        return
    cr.execute(
        """
        INSERT INTO maintenance_profile
            (resource_id, company_id, date_in_service, maintenance_team_id,
             technician_user_id, expected_mtbf, create_uid, create_date, write_uid, write_date)
        SELECT r.id, r.company_id, r.date_in_service, r.maintenance_team_id,
               r.technician_user_id, r.expected_mtbf, 1, now(), 1, now()
          FROM resource_resource r
         WHERE (r.maintenance_team_id IS NOT NULL
            OR r.technician_user_id IS NOT NULL
            OR COALESCE(r.expected_mtbf, 0) <> 0
            OR EXISTS (SELECT 1 FROM maintenance_order_resource_rel o WHERE o.resource_id = r.id)
            OR EXISTS (SELECT 1 FROM maintenance_plan_resource_rel p WHERE p.resource_id = r.id))
           AND NOT EXISTS (SELECT 1 FROM maintenance_profile m WHERE m.resource_id = r.id)
        """
    )
    for column in DROPPED:
        if column_exists(cr, "resource_resource", column):
            cr.execute(f'ALTER TABLE resource_resource DROP COLUMN "{column}"')  # noqa: E8501  a constant column name of this migration
