import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

REFLECTION_TABLES = (
    "ir_model_access",
    "ir_model_constraint",
    "ir_model_fields",
    "ir_model_inherit",
    "ir_model_relation",
    "ir_rule",
)


def migrate(cr, version):
    if not version:
        return
    orphans = _models_without_a_module(cr)
    if not orphans:
        return
    referenced = _referencing_rows(cr, list(orphans))
    for model_id, (model, table) in sorted(orphans.items(), key=lambda o: o[1]):
        rows = _count_rows(cr, table)
        if rows:
            _logger.warning(
                "model %r belongs to no installed module, but its table %r holds "
                "%s row(s); leaving both in place, because dropping the model "
                "drops the table and nothing else keeps those records",
                model,
                table,
                rows,
            )
            continue
        if referenced.get(model_id):
            _logger.warning(
                "model %r belongs to no installed module, but %s still name it; "
                "leaving it in place",
                model,
                ", ".join(sorted(referenced[model_id])),
            )
            continue
        _drop_model(cr, model_id, model, table)


def _models_without_a_module(cr):
    cr.execute(
        """
        SELECT m.id, m.model, to_regclass('public.' || replace(m.model, '.', '_'))
          FROM ir_model m
         WHERE m.state != 'manual'
           AND NOT EXISTS (
               SELECT 1
                 FROM ir_model_data d
                 JOIN ir_module_module mm ON mm.name = d.module
                WHERE d.model = 'ir.model' AND d.res_id = m.id
                  AND mm.state IN ('installed', 'to upgrade', 'to install')
           )
        """
    )
    return {id_: (model, table) for id_, model, table in cr.fetchall()}


def _referencing_rows(cr, model_ids):
    # The reflection tables describe the model itself and go with it; every other
    # row naming it is somebody's live record — an automation rule, a mail
    # template, a server action — and a model a live record names is not residue.
    referenced = {}
    cr.execute(
        """
        SELECT cl.relname, a.attname
          FROM pg_constraint c
          JOIN pg_class cl ON cl.oid = c.conrelid
          JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = c.conkey[1]
         WHERE c.contype = 'f'
           AND c.confrelid = 'ir_model'::regclass
           AND array_length(c.conkey, 1) = 1
           AND cl.relname != ALL(%s)
        """,
        [list(REFLECTION_TABLES)],
    )
    for table, column in cr.fetchall():
        cr.execute(
            SQL(
                "SELECT DISTINCT %(column)s FROM %(table)s WHERE %(column)s = ANY(%(ids)s)",
                column=SQL.identifier(column),
                table=SQL.identifier(table),
                ids=model_ids,
            )
        )
        for [model_id] in cr.fetchall():
            referenced.setdefault(model_id, set()).add(f"{table}.{column}")

    cr.execute(
        """
        SELECT o.id, f.model || '.' || f.name
          FROM ir_model_fields f
          JOIN ir_model o ON o.model = f.relation
         WHERE o.id = ANY(%s) AND f.model_id != o.id
        """,
        [model_ids],
    )
    for model_id, field in cr.fetchall():
        referenced.setdefault(model_id, set()).add(field)

    cr.execute(
        """
        SELECT o.id, cl.relname
          FROM ir_model o
          JOIN pg_constraint c
            ON c.confrelid = to_regclass('public.' || replace(o.model, '.', '_'))
          JOIN pg_class cl ON cl.oid = c.conrelid
         WHERE o.id = ANY(%s) AND c.contype = 'f' AND c.conrelid != c.confrelid
        """,
        [model_ids],
    )
    for model_id, table in cr.fetchall():
        referenced.setdefault(model_id, set()).add(table)
    return referenced


def _count_rows(cr, table):
    if table is None:
        return 0
    cr.execute(SQL("SELECT count(*) FROM %s", SQL.identifier(table)))
    return cr.fetchone()[0]


def _drop_model(cr, model_id, model, table):
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE (model = 'ir.model' AND res_id = %(id)s)
            OR (model = 'ir.model.fields'
                AND res_id IN (SELECT id FROM ir_model_fields WHERE model_id = %(id)s))
            OR (model = 'ir.model.access'
                AND res_id IN (SELECT id FROM ir_model_access WHERE model_id = %(id)s))
            OR (model = 'ir.rule'
                AND res_id IN (SELECT id FROM ir_rule WHERE model_id = %(id)s))
            OR model = %(model)s
        """,
        {"id": model_id, "model": model},
    )
    xml_ids = cr.rowcount
    cr.execute("DELETE FROM ir_model WHERE id = %s", [model_id])
    if table is not None:
        cr.execute(SQL("DROP TABLE %s", SQL.identifier(table)))
    _logger.info(
        "dropped model %r: it belongs to no installed module, %s, and nothing "
        "names it (%s external identifier(s) removed)",
        model,
        f"its table {table!r} was empty" if table else "it has no table",
        xml_ids,
    )
