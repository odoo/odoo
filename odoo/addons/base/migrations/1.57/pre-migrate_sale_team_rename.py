import logging

from odoo.db import schema
from odoo.tools import SQL
from odoo.tools.module_data import rename_in_stored_expressions

_logger = logging.getLogger(__name__)

OLD = "sales_team"
NEW = "sale_team"


def migrate(cr, version):
    if not version:
        return
    cr.execute("SELECT id FROM ir_module_module WHERE name = %s", [OLD])
    if not cr.fetchone():
        return
    _drop_placeholder(cr)
    _rename_module_row(cr)
    _rename_xmlids(cr)
    _rename_config_parameters(cr)
    _rename_stored_references(cr)


def _drop_placeholder(cr):
    cr.execute("SELECT id, state FROM ir_module_module WHERE name = %s", [NEW])
    if not (row := cr.fetchone()):
        return
    module_id, state = row
    if state != "uninstalled":
        raise ValueError(
            f"{OLD} and {NEW} are both present and {NEW} is {state}; "
            f"uninstall {NEW}, then upgrade base again"
        )
    cr.execute(
        "DELETE FROM ir_model_data WHERE module = 'base'"
        " AND model = 'ir.module.module' AND res_id = %s",
        [module_id],
    )
    cr.execute(
        "DELETE FROM ir_module_module_dependency WHERE module_id = %s", [module_id]
    )
    cr.execute(
        "DELETE FROM ir_module_module_exclusion WHERE module_id = %s", [module_id]
    )
    cr.execute("DELETE FROM ir_module_module WHERE id = %s", [module_id])
    _logger.info("dropped the uninstalled %s placeholder", NEW)


def _rename_module_row(cr):
    cr.execute(
        "UPDATE ir_module_module SET name = %s, data_file_checksums = NULL"
        " WHERE name = %s",
        [NEW, OLD],
    )
    for table in ("ir_module_module_dependency", "ir_module_module_exclusion"):
        cr.execute(
            SQL(
                """
                DELETE FROM %(table)s stale
                      WHERE stale.name = %(old)s
                        AND EXISTS (SELECT 1 FROM %(table)s kept
                                     WHERE kept.module_id = stale.module_id
                                       AND kept.name = %(new)s)
                """,
                table=SQL.identifier(table),
                old=OLD,
                new=NEW,
            )
        )
        cr.execute(
            SQL(
                "UPDATE %s SET name = %s WHERE name = %s",
                SQL.identifier(table),
                NEW,
                OLD,
            )
        )


def _rename_xmlids(cr):
    cr.execute(
        """
        SELECT d.name FROM ir_model_data d
         WHERE d.module = %s
           AND EXISTS (SELECT 1 FROM ir_model_data o
                        WHERE o.module = %s AND o.name = d.name)
        """,
        [OLD, NEW],
    )
    if clashing := sorted(name for (name,) in cr.fetchall()):
        raise ValueError(f"{OLD} and {NEW} both own {clashing}")
    cr.execute("UPDATE ir_model_data SET module = %s WHERE module = %s", [NEW, OLD])
    moved = cr.rowcount
    cr.execute(
        "UPDATE ir_model_data SET name = %s"
        " WHERE module = 'base' AND model = 'ir.module.module' AND name = %s",
        [f"module_{NEW}", f"module_{OLD}"],
    )
    _logger.info("renamed module %s to %s with %s xml id(s)", OLD, NEW, moved)


def _rename_config_parameters(cr):
    cr.execute(
        """
        UPDATE ir_config_parameter
           SET key = %s || substring(key from %s)
         WHERE key LIKE %s
           AND NOT EXISTS (
               SELECT 1 FROM ir_config_parameter existing
                WHERE existing.key = %s || substring(ir_config_parameter.key from %s)
           )
        """,
        [f"{NEW}.", len(OLD) + 2, _like_prefix(f"{OLD}."), f"{NEW}.", len(OLD) + 2],
    )


def _rename_stored_references(cr):
    rename_in_stored_expressions(cr, f"{OLD}.", f"{NEW}.")
    cr.execute(
        "UPDATE ir_ui_view SET key = %s || substring(key from %s) WHERE key LIKE %s",
        [f"{NEW}.", len(OLD) + 2, _like_prefix(f"{OLD}.")],
    )
    if schema.column_exists(cr, "ir_asset", "path"):
        cr.execute(
            "UPDATE ir_asset SET path = regexp_replace(path, %s, %s) WHERE path ~ %s",
            [f"^(/?){OLD}/", rf"\1{NEW}/", f"^/?{OLD}/"],
        )


def _like_prefix(prefix):
    return prefix.replace("_", "\\_") + "%"
