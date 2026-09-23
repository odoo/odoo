import logging
import typing

if typing.TYPE_CHECKING:
    from odoo.db.cursor import Cursor

_logger = logging.getLogger(__name__)

REBUILT_RELATIONS = ("sale_order_line_product_document_rel",)


def migrate(cr: Cursor, version: str | None) -> None:
    if not version:
        return

    for table in REBUILT_RELATIONS:
        cr.execute("SELECT to_regclass(%s)", (f"public.{table}",))
        if not cr.fetchone()[0]:
            continue
        cr.execute(
            """
            SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'public' AND table_name = %s
               AND column_name = 'product_document_id'
            """,
            (table,),
        )
        if not cr.fetchone():
            continue

        cr.execute(f'SELECT count(*) FROM "{table}"')
        rows = cr.fetchone()[0]
        if rows:
            _logger.warning(
                "%s still holds %d row(s) pointing at the dropped "
                "product.document; leaving it in place -- those links need "
                "remapping through ir_attachment before product_document goes",
                table,
                rows,
            )
            continue

        cr.execute(f'DROP TABLE "{table}"')
        _logger.info("Dropped empty %s so _auto_init rebuilds it", table)
