import logging

from odoo import Command
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestContactPhonePreference(TransactionCase):
    def test_phone_correction_preserves_selected_number(self):
        first = self.env["phone.number"].create(
            {"number": "+32000777005", "primary": True}
        )
        preferred = self.env["phone.number"].create(
            {"number": "+32000777006", "sequence": 100}
        )
        target = self.env["phone.number"].create(
            {"number": "+32000777007", "sequence": 200}
        )
        partner = self.env["res.partner"].create(
            {
                "name": "SMS correction",
                "phone_ids": [Command.set((first | preferred).ids)],
                "preferred_phone_id": preferred.id,
            }
        )
        partner._phone_replace_number("phone_ids", target.number)
        self.env.flush_all()
        self.env.invalidate_all()
        _logger.debug(
            "Phone correction: selected=%s requested=%s",
            partner._phone_get_number().id,
            target.id,
        )
        self.assertEqual(partner._phone_get_number(), target)
        self.assertIn(first, partner.phone_ids)
        self.assertNotIn(preferred, partner.phone_ids)

    def test_typed_correction_keeps_another_type_preferred(self):
        mobile = self.env["phone.number"].create(
            {"number": "+32000777008", "type": "mobile"}
        )
        landline = self.env["phone.number"].create(
            {"number": "+32000777009", "type": "landline"}
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Typed correction",
                "phone_ids": [Command.set((mobile | landline).ids)],
                "preferred_phone_id": landline.id,
            }
        )
        partner._phone_replace_number("phone_ids", "+32000777010", "mobile")
        self.assertEqual(partner._phone_get_number(), landline)
        self.assertEqual(partner._phone_get_number("mobile").number, "+32000777010")
        _logger.debug(
            "Typed correction: preferred=%s mobile=%s",
            landline.id,
            partner.main_mobile_id.id,
        )

    def test_correction_noop_and_clear_preserve_secondary(self):
        first = self.env["phone.number"].create(
            {"number": "+32000777011", "primary": True}
        )
        other = self.env["phone.number"].create({"number": "+32000777012"})
        partner = self.env["res.partner"].create(
            {
                "name": "Correction lifecycle",
                "phone_ids": [Command.set((first | other).ids)],
                "preferred_phone_id": first.id,
            }
        )
        partner._phone_replace_number("phone_ids", first.number)
        self.assertEqual(partner.phone_ids, first | other)
        self.assertEqual(partner.preferred_phone_id, first)
        partner._phone_replace_number("phone_ids", False)
        self.assertEqual(partner.phone_ids, other)
        self.assertFalse(partner.preferred_phone_id)
        _logger.debug("Correction clear: remaining=%s", partner.phone_ids.ids)
