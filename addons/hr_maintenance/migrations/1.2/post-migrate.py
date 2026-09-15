from odoo import SUPERUSER_ID, api
from odoo.db.schema import column_exists, table_exists


def migrate(cr, version):
    if (
        not version
        or not table_exists(cr, "maintenance_equipment")
        or not column_exists(cr, "maintenance_equipment", "asset_id")
        or not column_exists(cr, "maintenance_equipment", "equipment_assign_to")
    ):
        return
    env = api.Environment(
        cr, SUPERUSER_ID, {"tracking_disable": True, "active_test": False}
    )
    cr.execute(
        """
        SELECT asset.resource_id, employee.resource_id, equipment.department_id,
               start.date_start,
               CASE WHEN NOT equipment.active OR equipment.scrap_date IS NOT NULL
                    THEN GREATEST(
                        COALESCE(equipment.scrap_date::timestamp, now() at time zone 'UTC'),
                        start.date_start
                    )
               END
          FROM maintenance_equipment equipment
          CROSS JOIN LATERAL (
              SELECT COALESCE(equipment.assign_date::timestamp, equipment.create_date)
                         AS date_start
          ) start
          JOIN resource_asset asset ON asset.id = equipment.asset_id
     LEFT JOIN hr_employee employee
            ON employee.id = equipment.employee_id
           AND equipment.equipment_assign_to = 'employee'
         WHERE (equipment.equipment_assign_to = 'employee'
                AND equipment.employee_id IS NOT NULL)
            OR (equipment.equipment_assign_to = 'department'
                AND equipment.department_id IS NOT NULL)
        """
    )
    vals_list = []
    for resource_id, holder_id, department_id, date_start, date_end in cr.fetchall():
        vals = {
            "resource_id": resource_id,
            "role": "custodian",
            "date_start": date_start,
            "date_end": date_end,
        }
        if holder_id:
            vals["assignee_id"] = holder_id
        else:
            vals["department_id"] = department_id
        vals_list.append(vals)
    if vals_list:
        env["resource.assignment"].create(vals_list)
