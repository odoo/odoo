from odoo.db.schema import table_exists


def migrate(cr, version):
    if version and table_exists(cr, "maintenance_stage"):
        cr.execute("DROP TABLE maintenance_stage CASCADE")
