from odoo.db.schema import column_exists, table_exists

# the relation table each model's `tax_ids` actually uses, as the ORM derived it
TABLES = {
    "sale_order_line": ("account_tax_sale_order_line_rel", "sale_order_line_id"),
    "purchase_order_line": (
        "account_tax_purchase_order_line_rel",
        "purchase_order_line_id",
    ),
}


def migrate(cr, version):
    """Seed the tax shadow from what each line already carries.

    `tax_ids_auto_key` records the taxes the product and fiscal position WOULD
    give, so that a line whose taxes differ from it is recognised as manual. An
    existing row has no key, and an empty key beside non-empty taxes would read
    as an override -- freezing every line in the database against every future
    fiscal-position change. Seeding the key from the current taxes says "nothing
    was overridden before this migration", which is the only claim the data
    supports.
    """
    if not version:
        return
    for table, (rel, column) in TABLES.items():
        if not table_exists(cr, table) or not column_exists(
            cr, table, "tax_ids_auto_key"
        ):
            continue
        if not table_exists(cr, rel):
            continue
        cr.execute(
            f"""
            UPDATE {table} line
               SET tax_ids_auto_key = COALESCE(keys.key, '-')
              FROM (SELECT {column} AS line_id,
                           string_agg(account_tax_id::text, ',' ORDER BY account_tax_id) AS key
                      FROM {rel}
                  GROUP BY {column}) keys
             WHERE line.id = keys.line_id
            """
        )
        cr.execute(
            f"""
            UPDATE {table} SET tax_ids_auto_key = '-'
             WHERE tax_ids_auto_key IS NULL
               AND id NOT IN (SELECT {column} FROM {rel})
            """
        )
