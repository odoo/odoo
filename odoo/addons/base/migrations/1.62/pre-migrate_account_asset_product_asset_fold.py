import logging

from odoo.tools.module_data import remove_xmlid_records

_logger = logging.getLogger(__name__)

DISSOLVED = "account_asset_product_asset"


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT id FROM ir_module_module WHERE name = %s", (DISSOLVED,))
    row = cr.fetchone()
    if not row:
        return
    module_id = row[0]
    cr.execute("SELECT name FROM ir_model_data WHERE module = %s", (DISSOLVED,))
    names = [name for (name,) in cr.fetchall()]
    removed = remove_xmlid_records(cr, DISSOLVED, names) if names else 0
    cr.execute(
        "DELETE FROM ir_module_module_dependency WHERE module_id = %s OR name = %s",
        (module_id, DISSOLVED),
    )
    cr.execute(
        "DELETE FROM ir_model_data "
        "WHERE module = 'base' AND model = 'ir.module.module' AND res_id = %s",
        (module_id,),
    )
    cr.execute("DELETE FROM ir_module_module WHERE id = %s", (module_id,))
    _logger.info(
        "dropped %s: a board and its asset are one resource.asset now "
        "(%d record(s) of its views and fields removed)",
        DISSOLVED,
        removed,
    )
