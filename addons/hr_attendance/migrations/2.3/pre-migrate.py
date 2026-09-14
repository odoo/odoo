import logging
import uuid

from odoo.db.schema import column_exists

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Give every company a kiosk key before the column becomes NOT NULL.

    `res.company.attendance_kiosk_key` is now `required` and unique. `_auto_init`
    adds the NOT NULL, and it cannot add one over a NULL row, so any company
    still carrying one is filled here.

    A NULL was not only a schema problem. Every kiosk route is `auth="public"`
    and takes its token from the caller, and an Odoo domain turns `null`,
    `false` and `""` alike into `IS NULL` -- so a company with no key answered
    to a token of nothing. `_get_company()` refuses a falsy token now as well;
    this closes the other end.

    One `uuid4().hex` per row, not one for all of them: the column is unique,
    and two companies sharing a key would mean either one's kiosk answering to
    the other's token.
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
