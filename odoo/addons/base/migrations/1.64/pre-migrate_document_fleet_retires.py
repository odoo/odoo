from odoo.tools.module_data import remove_xmlid_records, retire_empty_module

MODULE = "document_fleet"
# The folder and the tag stay: the vehicle kind's own settings row keeps pointing
# at them, so a database's filed documents do not move.
KEPT_MODELS = ("document.document", "document.tag")


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT state FROM ir_module_module WHERE name = %s", [MODULE])
    row = cr.fetchone()
    if not row:
        return
    if row[0] == "uninstalled":
        # It shipped no records here, but the row still carries auto_install and
        # the module is gone from disk: retire it so the loader cannot pick it
        # up once fleet and document are both installed.
        retire_empty_module(cr, MODULE)
        return
    cr.execute(
        """
        UPDATE ir_module_module
           SET state = 'to install'
         WHERE name = 'document_resource_asset'
           AND state = 'uninstalled'
        """
    )
    cr.execute(
        "SELECT name FROM ir_model_data WHERE module = %s AND NOT model = ANY(%s)",
        [MODULE, list(KEPT_MODELS)],
    )
    remove_xmlid_records(cr, MODULE, [name for (name,) in cr.fetchall()])
    cr.execute(
        "UPDATE ir_model_data SET module = 'document_resource_asset' WHERE module = %s",
        [MODULE],
    )
    retire_empty_module(cr, MODULE)
