from odoo.tools.module_data import retire_empty_module

# ea6ec9d4d3e0 deleted enterprise's pos_account_reports (a manifest and one test,
# now point_of_sale/tests/test_pos_tax_report.py) and retired its module row from
# point_of_sale 1.0.9 -- which runs after the module graph is built with the row
# in it, so the loader reached the module, found the row gone and stopped with
# MissingError on every database that had it installed. A module absent from
# disk leaves the graph here, before it is assembled, as 1.59, 1.64 and 1.78 do.
MODULE = "pos_account_reports"


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT 1 FROM ir_module_module WHERE name = %s", [MODULE])
    if not cr.fetchone():
        return
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = %s AND model <> 'ir.module.module'",
        [MODULE],
    )
    retire_empty_module(cr, MODULE)
