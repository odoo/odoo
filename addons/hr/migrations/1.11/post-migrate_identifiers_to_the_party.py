import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

COLUMNS = {
    "identification_id": "NATIONAL_ID",
    "ssnid": "SSN",
    "passport_id": "PASSPORT",
    "barcode": "BADGE",
}


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "SELECT id, partner_id, identification_id, ssnid, passport_id, barcode,"
        " passport_expiration_date FROM hr_employee"
        " WHERE identification_id IS NOT NULL OR ssnid IS NOT NULL"
        " OR passport_id IS NOT NULL OR barcode IS NOT NULL"
    )
    rows = cr.fetchall()
    if not rows:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    types = {
        t.code: t
        for t in env["res.partner.identifier.type"].search(
            [("code", "in", list(COLUMNS.values()))]
        )
    }
    Identifier = env["res.partner.identifier"]
    held = {
        (i.partner_id.id, i.type_id.code)
        for i in Identifier.search([("type_id", "in", [t.id for t in types.values()])])
    }
    created = skipped = 0
    for employee_id, partner_id, *values in rows:
        passport_expiry = values.pop()
        for (column, code), value in zip(COLUMNS.items(), values, strict=True):
            if not value:
                continue
            if (partner_id, code) in held:
                skipped += 1
                continue
            vals = {"partner_id": partner_id, "type_id": types[code].id, "value": value}
            if code == "PASSPORT" and passport_expiry:
                vals["valid_until"] = passport_expiry
            try:
                with env.cr.savepoint():
                    Identifier.create(vals)
                created += 1
            except Exception as error:  # one bad value must not stop the rest
                skipped += 1
                _logger.warning(
                    "employee %s: %s %r not moved onto the party: %s",
                    employee_id,
                    column,
                    value,
                    error,
                    exc_info=True,
                )
    _logger.info(
        "identifiers moved onto the party: %s created, %s left in the old columns",
        created,
        skipped,
    )
