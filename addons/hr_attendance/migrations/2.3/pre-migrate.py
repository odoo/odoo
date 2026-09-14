import logging
import uuid

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Give every company a distinct kiosk key before the column becomes UNIQUE.

    NOT NULL IS NOT THE REASON, though it looks like it. `update_db_notnull`
    calls `_init_column` before scheduling the constraint, and this module
    overrides `_init_column` for exactly this column to back-fill every NULL --
    so a NULL key is filled with or without this script. Measured: a 2.2
    database with one NULL key upgrades to exit 0, NOT NULL added, key
    generated, with this directory moved aside.

    THE UNIQUE CONSTRAINT IS THE REASON. `_init_column` fills a NULL and leaves
    an EMPTY STRING alone, and two companies holding `''` collide. Odoo does
    not fail that upgrade -- it logs and carries on WITHOUT the index:

        WARNING odoo.schema: could not create unique index
        "res_company_attendance_kiosk_key_unique"
        DETAIL: Key (attendance_kiosk_key)=() is duplicated.

    Measured on two arms of one 2.2 database, two companies both holding `''`:
    without this script, exit 0, both keys still `''`, NO unique constraint on
    the table. With it, two distinct keys and the constraint present. So
    deleting this script does not fail an upgrade; it silently removes the
    protection the same commit claims to add, which is worse.

    The `''` rows are why the filter is not `IS NULL` alone, and one
    `uuid4().hex` per row is why the fill is a loop: a shared key would mean
    either company's kiosk answering to the other's token.

    The warning is the script's other job. `_init_column`'s back-fill is
    silent, and a company whose kiosk key changes has a kiosk URL that has
    stopped working with nothing anywhere saying so.
    """
    if not version or not column_exists(cr, "res_company", "attendance_kiosk_key"):
        return
    cr.execute(
        "SELECT id FROM res_company WHERE attendance_kiosk_key IS NULL "
        "OR attendance_kiosk_key = ''"
    )
    rows = cr.fetchall()
    if not rows:
        return
    cr.executemany(
        "UPDATE res_company SET attendance_kiosk_key = %s WHERE id = %s",
        [(uuid.uuid4().hex, company_id) for (company_id,) in rows],
    )
    _logger.warning(
        "hr_attendance: %s compan(ies) had no kiosk key and answered to a token "
        "of nothing on every public kiosk route; a fresh key was generated for "
        "each. Their kiosk URLs have changed.",
        len(rows),
    )
