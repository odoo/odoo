import logging

from odoo import SUPERUSER_ID, api
from odoo.db import schema

_logger = logging.getLogger(__name__)

IDENTIFIER_CODES = {
    "identification_id": "NATIONAL_ID",
    "ssnid": "SSN",
    "passport_id": "PASSPORT",
    "barcode": "BADGE",
}


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"active_test": False})
    _split_shared_parties(cr, env)
    _sync_resource_active(cr)
    _sync_employee_names(cr)
    env.invalidate_all()


def _split_shared_parties(cr, env):
    # The rebinding is SQL on purpose: hr.employee.write's party follow-ups treat
    # the party an employee leaves last as that employee's own, and would hand it
    # every remaining identifier and archive it, the generic partner included.
    cr.execute(
        """
        SELECT e.id, e.partner_id, e.name, e.private_address_id, e.active
          FROM hr_employee e
          JOIN res_partner p ON p.id = e.partner_id
         WHERE e.name IS DISTINCT FROM p.name
           AND EXISTS (
               SELECT 1 FROM hr_employee other
                WHERE other.partner_id = e.partner_id
                  AND other.company_id = e.company_id
                  AND other.id <> e.id)
         ORDER BY e.partner_id, e.id
        """
    )
    misbound = cr.fetchall()
    if not misbound:
        return
    employee_ids = [row[0] for row in misbound]
    homes = _assign_own_homes(cr, misbound)
    stale_values = _read_stale_identifiers(cr, employee_ids)
    for employee_id, former_id, name, _home_id, active in misbound:
        party, reused = _get_or_create_own_party(env, name)
        if active and not party.active:
            party.active = True
        env.flush_all()
        home_id = homes[employee_id]
        cr.execute(
            "UPDATE hr_employee SET partner_id = %s, private_address_id = %s"
            " WHERE id = %s",
            [party.id, home_id, employee_id],
        )
        cr.execute(
            "UPDATE resource_resource r SET partner_id = %s, name = %s"
            " FROM hr_employee e WHERE e.id = %s AND r.id = e.resource_id",
            [party.id, name, employee_id],
        )
        if home_id:
            cr.execute(
                "UPDATE res_partner SET parent_id = %s WHERE id = %s",
                [party.id, home_id],
            )
        cr.execute(
            """
            UPDATE res_partner_bank bank
               SET partner_id = %s
              FROM employee_bank_account_rel rel
             WHERE rel.employee_id = %s
               AND rel.bank_account_id = bank.id
               AND bank.partner_id = %s
            """,
            [party.id, employee_id, former_id],
        )
        moved = _move_stale_identifiers(
            cr, former_id, party.id, stale_values.get(employee_id, {})
        )
        _logger.info(
            "employee %s left shared party %s for party %s (%s), home %s, "
            "identifiers moved: %s",
            employee_id,
            former_id,
            party.id,
            "reused" if reused else "created",
            home_id,
            moved,
        )


def _assign_own_homes(cr, misbound):
    cr.execute(
        "SELECT private_address_id, count(*) FROM hr_employee"
        " WHERE private_address_id IS NOT NULL GROUP BY private_address_id"
    )
    residents = dict(cr.fetchall())
    former_ids = sorted({row[1] for row in misbound})
    cr.execute(
        "SELECT parent_id, id FROM res_partner"
        " WHERE parent_id = ANY(%s) AND type = 'private' ORDER BY id",
        [former_ids],
    )
    spare = {}
    for parent_id, home_id in cr.fetchall():
        if home_id not in residents:
            spare.setdefault(parent_id, []).append(home_id)
    homes = {}
    kept = set()
    for employee_id, former_id, _name, home_id, _active in misbound:
        if home_id and (residents[home_id] == 1 or home_id not in kept):
            kept.add(home_id)
            homes[employee_id] = home_id
        else:
            available = spare.get(former_id, [])
            homes[employee_id] = available.pop(0) if available else None
    return homes


def _read_stale_identifiers(cr, employee_ids):
    values = {}
    for fname, code in IDENTIFIER_CODES.items():
        if not schema.column_exists(cr, "hr_employee", fname):
            continue
        cr.execute(
            "SELECT id, value FROM ("
            " SELECT id, (to_jsonb(e) ->> %s) AS value FROM hr_employee e"
            " WHERE id = ANY(%s)) v WHERE value IS NOT NULL AND value <> ''",
            [fname, employee_ids],
        )
        for employee_id, value in cr.fetchall():
            values.setdefault(employee_id, {})[code] = value
    return values


def _get_or_create_own_party(env, name):
    candidates = env["res.partner"].search(
        [
            ("name", "=", name),
            ("is_company", "=", False),
            ("parent_id", "=", False),
            ("type", "=", "contact"),
            ("employee_ids", "=", False),
            ("user_ids", "=", False),
            ("resource_ids", "=", False),
        ]
    )
    if len(candidates) == 1:
        return candidates, True
    return env["res.partner"].create({"name": name}), False


def _move_stale_identifiers(cr, former_id, party_id, stale_values):
    moved = []
    for code, value in stale_values.items():
        cr.execute(
            """
            UPDATE res_partner_identifier identifier
               SET partner_id = %s
              FROM res_partner_identifier_type kind
             WHERE kind.id = identifier.type_id
               AND kind.code = %s
               AND identifier.partner_id = %s
               AND identifier.value = %s
               AND NOT EXISTS (
                   SELECT 1 FROM res_partner_identifier held
                    WHERE held.partner_id = %s AND held.type_id = kind.id)
            """,
            [party_id, code, former_id, value, party_id],
        )
        if cr.rowcount:
            moved.append(code)
    return moved


def _sync_resource_active(cr):
    cr.execute(
        """
        UPDATE resource_resource r
           SET active = e.active
          FROM hr_employee e
         WHERE e.resource_id = r.id
           AND r.active IS DISTINCT FROM e.active
     RETURNING r.id
        """
    )
    resynced = [row[0] for row in cr.fetchall()]
    _logger.info(
        "%s employee resources archived or restored with their employee: %s",
        len(resynced),
        resynced,
    )


def _sync_employee_names(cr):
    cr.execute(
        """
        UPDATE hr_employee e
           SET name = p.name
          FROM res_partner p
         WHERE p.id = e.partner_id
           AND p.name IS NOT NULL
           AND e.name IS DISTINCT FROM p.name
     RETURNING e.id
        """
    )
    renamed = [row[0] for row in cr.fetchall()]
    _logger.info(
        "%s employees took their party's name again: %s", len(renamed), renamed
    )
