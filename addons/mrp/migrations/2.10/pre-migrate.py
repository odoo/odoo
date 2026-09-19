from odoo.db import schema
from odoo.tools import SQL


def migrate(cr, version):
    if not version:
        return
    # 2.9 as first published dropped these two as projections of the resource;
    # a work centre names and archives itself now, so a database that ran it
    # takes the columns back from the resource before the ORM sets NOT NULL.
    for column, sql_type in (("name", "varchar"), ("active", "boolean")):
        if schema.column_exists(cr, "mrp_workcenter", column):
            continue
        schema.create_column(cr, "mrp_workcenter", column, sql_type)
        cr.execute(
            SQL(
                """
                UPDATE mrp_workcenter AS workcenter
                   SET %(column)s = resource.%(column)s
                  FROM resource_resource AS resource
                 WHERE resource.id = workcenter.resource_id
                """,
                column=SQL.identifier(column),
            )
        )
