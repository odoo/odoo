"""Pre-migration: ``base_sparse_field`` is deleted from the tree.

Nothing depended on it and nothing in the tree declared a ``fields.Serialized``
or a ``sparse=`` field, so the module's only footprint in a database that
installed it is its own: the ``sparse_fields.test`` model and table, the
``serialization_field_id`` column it grafted on ``ir_model_fields``, the
``serialized`` value it added to ``ir.model.fields.ttype``, one inherited form
view, one access row, and the module row itself.

This runs in ``base`` because the row has to go before the graph is assembled.
Left alone, the loader finds the module installed and absent from disk, warns
``not installable, skipped``, and then fails the load with ``Some modules have
inconsistent states after upgrade`` on every run after it (base 1.40 measured
the same for ``iot_base``).

The records behind the module's xml ids are deleted here rather than left to
``_process_end``, which only reaps records of modules it loaded. The
``serialized`` selection row is left to ``base``'s own reflection of
``ttype``, which drops values the field no longer declares. The module's
``base.module_<name>`` xml id goes with the row, or a database that already
refreshed its module list against the new tree fails on the unique index
(base 1.53, 02934af69c33).
"""

import logging

_logger = logging.getLogger(__name__)

MODULE = "base_sparse_field"
MODEL = "sparse_fields.test"


def migrate(cr, version):
    cr.execute("SELECT id, state FROM ir_module_module WHERE name = %s", (MODULE,))
    row = cr.fetchone()
    if not row:
        return
    module_id, state = row

    cr.execute(
        """
        DELETE FROM ir_ui_view
         WHERE id IN (
            SELECT res_id FROM ir_model_data
             WHERE module = %s AND model = 'ir.ui.view'
         )
        """,
        (MODULE,),
    )
    cr.execute("DELETE FROM ir_model WHERE model = %s", (MODEL,))
    cr.execute(
        "DELETE FROM ir_model_fields WHERE model = 'ir.model.fields'"
        " AND name = 'serialization_field_id'"
    )
    cr.execute(
        "ALTER TABLE ir_model_fields DROP COLUMN IF EXISTS serialization_field_id"
    )
    cr.execute("DROP TABLE IF EXISTS sparse_fields_test")
    cr.execute("DELETE FROM ir_model_constraint WHERE module = %s", (module_id,))
    cr.execute("DELETE FROM ir_model_relation WHERE module = %s", (module_id,))
    cr.execute("DELETE FROM ir_model_data WHERE module = %s", (MODULE,))
    owned = cr.rowcount

    cr.execute(
        "DELETE FROM ir_module_module_dependency WHERE name = %s OR module_id = %s",
        (MODULE, module_id),
    )
    cr.execute("DELETE FROM ir_module_module_exclusion WHERE name = %s", (MODULE,))
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'base' AND model = 'ir.module.module' AND res_id = %s
        """,
        (module_id,),
    )
    cr.execute("DELETE FROM ir_module_module WHERE id = %s", (module_id,))
    _logger.info(
        "base 1.55: dropped the %s module row, which was %s, and its %d xml id(s)",
        MODULE,
        state,
        owned,
    )
