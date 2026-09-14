import logging

from odoo import Command
from odoo.tests import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestMainChannelsPickTheRightRecord(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Main Channels"})

    def _number(self, number, phone_type, **extra):
        return self.env["phone.number"].create(
            {"number": number, "type": phone_type, **extra}
        )

    def test_the_main_phone_is_the_first_landline_and_the_mobile_the_first_mobile(self):
        far = self._number("+52 55 1111 1111", "landline", sequence=20)
        near = self._number("+52 55 2222 2222", "landline", sequence=5)
        mobile = self._number("+52 55 3333 3333", "mobile")
        fax = self._number("+52 55 4444 4444", "fax")
        self.partner.phone_ids = far + near + mobile + fax

        self.assertEqual(self.partner.main_phone_id, near)
        self.assertEqual(self.partner.main_mobile_id, mobile)

    def test_the_order_holds_without_an_intervening_invalidation(self):
        far = self._number("+52 55 1111 1111", "landline", sequence=20)
        near = self._number("+52 55 2222 2222", "landline", sequence=5)
        self.partner.phone_ids = far + near

        self.assertEqual(self.partner.main_phone_id, near)

        self.env.invalidate_all()
        self.assertEqual(self.partner.main_phone_id, near)

    def test_primary_outranks_sequence(self):
        first = self._number("+52 55 1111 1111", "landline", sequence=5)
        marked = self._number("+52 55 2222 2222", "landline", sequence=20)
        self.partner.phone_ids = first + marked
        self.assertEqual(self.partner.main_phone_id, first)

        marked.primary = True
        self.assertEqual(self.partner.main_phone_id, marked)

    def test_an_archived_number_is_not_the_main_one(self):
        kept = self._number("+52 55 1111 1111", "landline", sequence=20)
        archived = self._number("+52 55 2222 2222", "landline", sequence=5)
        self.partner.phone_ids = kept + archived
        self.assertEqual(self.partner.main_phone_id, archived)

        archived.active = False
        self.assertEqual(self.partner.main_phone_id, kept)

    def test_a_contact_with_no_number_of_that_type_has_no_main_one(self):
        self.partner.phone_ids = self._number("+52 55 3333 3333", "mobile")
        self.assertFalse(self.partner.main_phone_id)
        self.assertEqual(self.partner.main_mobile_id.number, "+52 55 3333 3333")

    def test_the_main_bank_account_is_the_first_active_one(self):
        Bank = self.env["res.partner.bank"]
        far = Bank.create(
            {"acc_number": "MAIN-1", "partner_id": self.partner.id, "sequence": 20}
        )
        near = Bank.create(
            {"acc_number": "MAIN-2", "partner_id": self.partner.id, "sequence": 5}
        )
        self.assertEqual(self.partner.main_bank_id, near)

        near.active = False
        self.assertEqual(self.partner.main_bank_id, far)

    def test_they_are_stored_so_a_domain_and_a_group_by_reach_them(self):
        mobile = self._number("+52 55 3333 3333", "mobile")
        self.partner.phone_ids = mobile
        self.env["res.partner.bank"].create(
            {"acc_number": "MAIN-3", "partner_id": self.partner.id}
        )
        self.env.flush_all()

        Partner = self.env["res.partner"]
        self.assertEqual(
            Partner.search([("main_mobile_id", "=", mobile.id)]), self.partner
        )
        grouped = Partner._read_group(
            [("id", "=", self.partner.id)], ["main_bank_id"], ["__count"]
        )
        self.assertEqual(grouped[0][0], self.partner.main_bank_id)

    def test_preference_lifecycle_and_typed_selection(self):
        self.partner.phone_ids = [
            Command.create({"number": "+32000111001", "primary": True}),
            Command.create({"number": "+32000111002", "type": "emergency"}),
        ]
        numbers = self.partner.phone_ids
        first, second = numbers
        second.type = "landline"
        self.partner.preferred_phone_id = second
        _logger.debug(
            "Preference lifecycle: partner=%s preferred=%s", self.partner.id, second.id
        )
        self.assertEqual(self.partner._phone_get_number(), second)
        self.assertEqual(self.partner._phone_get_number("mobile"), first)
        self.assertEqual(self.partner.main_phone_id, second)
        self.assertEqual(self.partner.main_mobile_id, first)
        second.active = False
        self.assertEqual(
            self.partner.with_context(active_test=False)._phone_get_number(), first
        )
        self.assertFalse(self.partner.main_phone_id)
        second.active = True
        self.assertEqual(self.partner._phone_get_number(), second)
        copied = self.partner.copy()
        self.assertEqual(copied._phone_get_number(), second)
        self.partner.phone_ids = [Command.unlink(second.id)]
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertFalse(self.partner.preferred_phone_id)
        self.assertEqual(self.partner._phone_get_number(), first)
        self.assertEqual(copied._phone_get_number(), second)
        copied.phone_ids = [Command.clear()]
        self.assertFalse(copied.preferred_phone_id)
        self.assertFalse(copied._phone_get_number())

    def test_reverse_unlink_clears_preference(self):
        selected = self._number("+32000111002", "mobile")
        self.partner.phone_ids = selected
        self.partner.preferred_phone_id = selected
        selected.partner_ids = [Command.unlink(self.partner.id)]
        self.env.flush_all()
        self.env.invalidate_all()
        _logger.debug(
            "Reverse unlink: preference=%s", self.partner.preferred_phone_id.id
        )
        self.assertFalse(self.partner.preferred_phone_id)
        self.assertNotEqual(self.partner._phone_get_number(), selected)

    def test_unrelated_preference_is_rejected(self):
        from odoo.exceptions import ValidationError

        unrelated = self.env["phone.number"].create({"number": "+32000111009"})
        with self.assertRaises(ValidationError):
            self.partner.preferred_phone_id = unrelated

    def test_deleting_preferred_number_restores_fallback(self):
        selected = self._number("+32000111012", "mobile")
        fallback = self._number("+32000111013", "mobile")
        self.partner.write(
            {
                "phone_ids": [Command.set((selected | fallback).ids)],
                "preferred_phone_id": selected.id,
            }
        )
        selected.unlink()
        self.env.flush_all()
        self.env.invalidate_all()
        _logger.debug(
            "Phone deletion: selected=%s", self.partner._phone_get_number().id
        )
        self.assertFalse(self.partner.preferred_phone_id)
        self.assertEqual(self.partner._phone_get_number(), fallback)
        self.assertEqual(self.partner.main_mobile_id, fallback)

    def test_selection_is_stable_for_empty_and_unsorted_relations(self):
        self.assertFalse(self.env["res.partner"]._phone_get_number())
        first = self._number("+32000111014", "mobile")
        second = self._number("+32000111015", "mobile")
        self.partner.phone_ids = second | first
        self.assertEqual(self.partner._phone_get_number(), first)
        self.env.invalidate_all()
        self.assertEqual(self.partner._phone_get_number(), first)
        _logger.debug("Stable tie selection: selected=%s", first.id)

        draft = self.env["res.partner"].new(
            {
                "name": "Unsaved phones",
                "phone_ids": [
                    Command.create({"number": "DRAFT-1"}),
                    Command.create({"number": "DRAFT-2"}),
                ],
            }
        )
        _logger.debug("Draft selection: records=%s", len(draft.phone_ids))
        self.assertEqual(draft._phone_get_number(), draft.phone_ids[:1])
        draft.preferred_phone_id = draft.phone_ids[-1:]
        self.assertEqual(draft._phone_get_number(), draft.phone_ids[-1:])

    def test_preference_survives_merge_of_source_contact(self):
        preferred = self._number("+32000777001", "mobile", sequence=100)
        global_first = self._number("+32000777002", "mobile", primary=True)
        source = self.env["res.partner"].create(
            {
                "name": "Preferred source",
                "phone_ids": [Command.set((global_first | preferred).ids)],
                "preferred_phone_id": preferred.id,
            }
        )
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})
        wizard._merge((self.partner | source).ids, self.partner, extra_checks=False)
        self.env.flush_all()
        self.env.invalidate_all()
        _logger.debug(
            "Merged preference: selected=%s expected=%s",
            self.partner._phone_get_number().id,
            preferred.id,
        )
        self.assertEqual(self.partner._phone_get_number(), preferred)
        self.assertEqual(self.partner.preferred_phone_id, preferred)

    def test_preference_write_order_and_archived_copy(self):
        first = self._number("+32000777003", "mobile", primary=True)
        preferred = self._number("+32000777004", "mobile", sequence=100)
        self.partner.write(
            {
                "preferred_phone_id": preferred.id,
                "phone_ids": [Command.set((first | preferred).ids)],
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        self.assertEqual(self.partner._phone_get_number(), preferred)
        preferred.active = False
        copied = self.partner.copy()
        _logger.debug(
            "Archived preference copy: source=%s copy=%s", self.partner.id, copied.id
        )
        self.assertEqual(copied._phone_get_number(), first)
        preferred.active = True
        self.assertEqual(copied._phone_get_number(), preferred)

    def test_merge_respects_destination_preference_and_absorption_option(self):
        for absorb in (False, True):
            with self.subTest(absorb=absorb):
                chosen = self._number(
                    f"+320007771{int(absorb)}1", "mobile", sequence=100
                )
                incoming = self._number(
                    f"+320007771{int(absorb)}2", "mobile", primary=True
                )
                destination = self.env["res.partner"].create(
                    {
                        "name": "Destination choice",
                        "phone_ids": [Command.link(chosen.id)],
                        "preferred_phone_id": chosen.id,
                    }
                )
                source = self.env["res.partner"].create(
                    {
                        "name": "Source choice",
                        "phone_ids": [Command.link(incoming.id)],
                        "preferred_phone_id": incoming.id,
                    }
                )
                wizard = self.env["base.partner.merge.automatic.wizard"].create(
                    {"absorb_source_values": absorb}
                )
                wizard._merge(
                    (destination | source).ids, destination, extra_checks=False
                )
                self.assertEqual(destination._phone_get_number(), chosen)
                self.assertEqual(incoming in destination.phone_ids, absorb)
                _logger.debug(
                    "Merge preference policy: absorb=%s selected=%s", absorb, chosen.id
                )
