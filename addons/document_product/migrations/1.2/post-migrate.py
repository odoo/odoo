"""Drop ``product.document`` (1.2).

Contract step of the product-document dissolution. 1.1 backfilled every
``product.document`` into a ``documents.document`` over the same attachment and
copied the discriminator columns across; this drops what is left.

Ordering matters and is why the drop lives here rather than in `product`:
`documents_product` is the module that owns both halves of the move, so 1.1 is
guaranteed to have run against this database before 1.2 does. Re-running the
backfill first is deliberate belt-and-braces -- a database upgraded straight from
a version predating 1.1 would otherwise lose rows.

Everything that still points at the table has to be carried over first, and
that is what ``_carry_references_over`` does. A ``product.document`` id is not a
``documents.document`` id, so leaving those references alone is worse than
losing them: ``mrp.eco.displayed_image_id`` now targets ``documents.document``
and its stored numbers would silently address the wrong record, while a relation
table would keep rows whose target no longer exists. The bridge between the two
is the attachment they share -- 1.1 matched on ``ir_attachment_id`` to create
them, so the same join maps old id to new.

Relation tables need their shape moved too, not just their values. This module
is core and runs long before the addons that own those m2m fields, so their new
tables do not exist yet when this migration executes -- which is precisely why
a remap written anywhere later cannot work, and why the table is renamed into
the shape ``_auto_init`` will look for. When that name is already taken (an
earlier ``_auto_init`` got there first) the rows are moved into it instead.

Rows whose ``product.document`` never gained a ``documents.document`` cannot be
carried: a relation row is deleted and a column is nulled, because a dangling
foreign key is not a thing Postgres will let us leave behind either way. After
1.1 has run, that set is empty.

The attachments are NOT touched. ``product.document`` cascade-deleted its
attachment on unlink, but every one of these attachments is now carried by a
``documents.document``, so dropping the table must leave them alone. Deleting the
``ir_model`` row is what removes the model's fields, constraints and ACLs, and
the ORM would otherwise resurrect the table on the next registry load.
"""

import logging

from odoo.db.schema import table_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not table_exists(cr, "product_document"):
        return

    _rerun_backfill(cr)

    cr.execute("SELECT count(*) FROM product_document")
    remaining = cr.fetchone()[0]

    # The satellites -- ACL rows and the multi-company rule -- cascade when the
    # `ir_model` row goes, which leaves their xmlids pointing at nothing.
    # `_process_end` cannot sweep those afterwards: it removes a record and then
    # its xmlid, and by then the record is already gone. So drop the xmlids while
    # the ids are still resolvable.
    for model, table in (("ir.access", "ir_access"),):
        cr.execute(
            f"""
            DELETE FROM ir_model_data
                  WHERE model = %s
                    AND res_id IN (
                            SELECT s.id
                              FROM {table} s
                              JOIN ir_model m ON m.id = s.model_id
                             WHERE m.model = 'product.document'
                        )
            """,
            [model],
        )
    cr.execute(
        """
        DELETE FROM ir_model_data
              WHERE model = 'ir.model.fields'
                AND res_id IN (
                        SELECT f.id
                          FROM ir_model_fields f
                          JOIN ir_model m ON m.id = f.model_id
                         WHERE m.model = 'product.document'
                    )
        """
    )
    cr.execute(
        """
        DELETE FROM ir_model_data
              WHERE model = 'ir.model'
                AND res_id IN (SELECT id FROM ir_model WHERE model = 'product.document')
        """
    )
    # The ir_model_fields and ir_access ROWS cascade from here;
    # their xmlids were dropped above, while their ids still resolved.
    cr.execute("DELETE FROM ir_model WHERE model = 'product.document'")
    _carry_references_over(cr)
    cr.execute("DROP TABLE product_document")

    _logger.info(
        "product.document dropped; %s row(s) had already been carried over to "
        "documents.document",
        remaining,
    )


def _rerun_backfill(cr):
    """Idempotent, so running 1.1's pass again only fills gaps."""
    import importlib.util
    import pathlib

    path = pathlib.Path(__file__).parents[1] / "1.1" / "post-migrate.py"
    spec = importlib.util.spec_from_file_location("_backfill_1_1", path)
    backfill = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backfill)
    backfill.migrate(cr, "1.1")


def _carry_references_over(cr):
    """Repoint every reference to a ``product.document`` at its ``documents.document``."""
    cr.execute(
        """
        CREATE TEMP TABLE pd_map ON COMMIT DROP AS
        SELECT pd.id AS old_id, dd.id AS new_id
          FROM product_document pd
          JOIN documents_document dd ON dd.attachment_id = pd.ir_attachment_id
        """
    )
    cr.execute("SELECT count(*) FROM pd_map")
    mapped = cr.fetchone()[0]

    cr.execute(
        """
        SELECT DISTINCT c.conrelid::regclass::text, a.attname, c.conname
          FROM pg_constraint c
          JOIN pg_attribute a
            ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
         WHERE c.confrelid = 'product_document'::regclass
           AND c.contype = 'f'
         ORDER BY 1, 2
        """
    )
    references = cr.fetchall()

    # Release the keys before rewriting through them. A carried value is a
    # `documents.document` id, which `product_document` does not contain, so
    # every one of these updates would be rejected while the key still stands.
    # They are discovered first for the same reason -- dropping them is what
    # erases the record of who pointed here.
    for table, _column, constraint in references:
        cr.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT "{constraint}"')

    for table, column, _constraint in references:
        # An m2m leg is named after its comodel's table; anything else is a
        # plain many2one and keeps both its name and its place.
        is_relation = column == "product_document_id" and table.endswith("_rel")

        if is_relation:
            cr.execute(
                f'DELETE FROM "{table}"'
                f' WHERE "{column}" NOT IN (SELECT old_id FROM pd_map)'
            )
        else:
            cr.execute(
                f'UPDATE "{table}" SET "{column}" = NULL'
                f' WHERE "{column}" IS NOT NULL'
                f'   AND "{column}" NOT IN (SELECT old_id FROM pd_map)'
            )
        stranded = cr.rowcount

        cr.execute(
            f'UPDATE "{table}" t SET "{column}" = m.new_id'
            f'  FROM pd_map m WHERE t."{column}" = m.old_id'
        )
        carried = cr.rowcount

        landed = _rehome_relation_table(cr, table, column) if is_relation else table
        _logger.info(
            "%s.%s -> %s: carried %d reference(s), stranded %d, over %d mapped "
            "document(s)",
            table,
            column,
            landed,
            carried,
            stranded,
            mapped,
        )


def _rehome_relation_table(cr, table, column):
    """Give the m2m table the name and column ``_auto_init`` will expect."""
    cr.execute(
        f'ALTER TABLE "{table}" RENAME COLUMN "{column}" TO "documents_document_id"'
    )
    prefix = "product_document_"
    if not table.startswith(prefix):
        return table  # e.g. sale_order_line_product_document_rel keeps its name

    target = "documents_document_" + table[len(prefix) :]
    cr.execute("SELECT to_regclass(%s)", (f"public.{target}",))
    if cr.fetchone()[0] is None:
        cr.execute(f'ALTER TABLE "{table}" RENAME TO "{target}"')
        return target

    cr.execute(
        """
        SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position)
          FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = %s
        """,
        (table,),
    )
    columns = cr.fetchone()[0]
    cr.execute(
        f'INSERT INTO "{target}" ({columns})'
        f' SELECT {columns} FROM "{table}" ON CONFLICT DO NOTHING'
    )
    cr.execute(f'DROP TABLE "{table}"')
    return target
