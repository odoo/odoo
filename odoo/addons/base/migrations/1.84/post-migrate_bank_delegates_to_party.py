import logging

from odoo import SUPERUSER_ID, api
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
    if not version or not column_exists(cr, "res_bank", "name"):
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute(
        f"SELECT id, {', '.join(COLUMNS)} FROM res_bank WHERE partner_id IS NULL ORDER BY id"
    )
    rows = cr.fetchall()
    if not rows:
        return
    parties = env["res.partner"].create(
        [
            {
                "name": name,
                "street": street,
                "street2": street2,
                "zip": zip_,
                "city": city,
                "state_id": state,
                "country_id": country,
                "email": email,
                "active": active if active is not None else True,
                "is_company": True,
            }
            for _id, name, street, street2, zip_, city, state, country, email, active in rows
        ]
    )
    for (bank_id, *_rest), party in zip(rows, parties, strict=True):
        cr.execute(
            "UPDATE res_bank SET partner_id = %s WHERE id = %s", [party.id, bank_id]
        )
    _logger.info("res_bank: %s banks given a party of their own", len(rows))
    if table_exists(cr, "res_bank_phone_number_rel"):
        cr.execute(
            """
            INSERT INTO res_partner_phone_number_rel (partner_id, phone_number_id)
                 SELECT b.partner_id, r.phone_number_id
                   FROM res_bank_phone_number_rel r
                   JOIN res_bank b ON b.id = r.bank_id
            ON CONFLICT DO NOTHING
            """
        )
