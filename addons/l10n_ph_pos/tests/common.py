# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_ph_invoice.models.l10n_ph_discount_privilege import (
    PARTNER_IDENTIFIER_KEYS,
)


def make_holder_vals(env, privilege, name, id_number):
    """
    Holder values, as sent by the POS, for the contact named ``name``
    (created as needed), given ``id_number`` as their ID of ``privilege``'s
    type.
    """
    partner = env["res.partner"].search([("name", "=", name)], limit=1) or env["res.partner"].create({"name": name})
    key = PARTNER_IDENTIFIER_KEYS[privilege.discount_type]
    partner.additional_identifiers = {**(partner.additional_identifiers or {}), key: id_number}
    return {"privilege_id": privilege.id, "partner_id": partner.id}
