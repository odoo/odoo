import logging

from odoo.db.schema import column_exists, drop_constraint

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'res_company'::regclass AND conname = 'res_company_name_uniq'
        """
    )
    if cr.fetchone():
        drop_constraint(cr, "res_company", "res_company_name_uniq")
    if not column_exists(cr, "res_company", "name"):
        return
    # a report's view or materialized view may still select the column: the
    # loader rebuilds every Odoo-owned relation once the registry is loaded,
    # so dropping it here costs nothing; a relation nobody owns is named
    cr.execute(
        """
        SELECT DISTINCT dependent.relname, dependent.relkind
          FROM pg_depend
          JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
          JOIN pg_class dependent ON pg_rewrite.ev_class = dependent.oid
          JOIN pg_attribute ON pg_depend.refobjid = pg_attribute.attrelid
                           AND pg_depend.refobjsubid = pg_attribute.attnum
         WHERE pg_depend.refobjid = 'res_company'::regclass
           AND pg_attribute.attname = 'name'
        """
    )
    for relname, relkind in cr.fetchall():
        _logger.warning(
            "res_company.name is dropped: the %s %s selected it and is dropped "
            "with it; a report's relation is rebuilt at the end of the load",
            "materialized view" if relkind == "m" else "view",
            relname,
        )
    cr.execute("ALTER TABLE res_company DROP COLUMN name CASCADE")
