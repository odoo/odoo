import logging

from odoo.db.schema import column_exists, table_exists

_logger = logging.getLogger(__name__)

COLUMNS = (
    "name",
    "street",
    "street2",
    "zip",
    "city",
    "state",
    "country",
    "email",
    "active",
)


def migrate(cr, version):
    if not version:
        return
    for column in COLUMNS:
        if not column_exists(cr, "res_bank", column):
            continue
        cr.execute(
            """
            SELECT DISTINCT dependent.relname
              FROM pg_depend
              JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
              JOIN pg_class dependent ON pg_rewrite.ev_class = dependent.oid
              JOIN pg_attribute ON pg_depend.refobjid = pg_attribute.attrelid
                               AND pg_depend.refobjsubid = pg_attribute.attnum
             WHERE pg_depend.refobjid = 'res_bank'::regclass
               AND pg_attribute.attname = %s
            """,
            [column],
        )
        for (relname,) in cr.fetchall():
            _logger.warning(
                "res_bank.%s is dropped: the relation %s selected it and is dropped "
                "with it; a report's relation is rebuilt at the end of the load",
                column,
                relname,
            )
        cr.execute(f"ALTER TABLE res_bank DROP COLUMN {column} CASCADE")
    if table_exists(cr, "res_bank_phone_number_rel"):
        cr.execute("DROP TABLE res_bank_phone_number_rel")
