from contextlib import contextmanager
from unittest.mock import patch

from odoo import Command, models
from odoo.exceptions import (
    AccessError,
    RedirectWarning,
    UserError,
    ValidationError,
)
from odoo.libs.email import extract_rfc2822_addresses
from odoo.tests import Form
from odoo.tests.common import TransactionCase, new_test_user, tagged, users

from odoo.addons.base.models import res_partner as res_partner_module
from odoo.addons.base.models.res_partner import ResPartner
from odoo.addons.base.tests.common import TransactionCaseWithUserDemo

SAMPLES = [
    (
        '"Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr> ',
        "Raoul Grosbedon",
        "raoul@chirurgiens-dentistes.fr",
    ),
    (
        "ryu+giga-Sushi@aizubange.fukushima.jp",
        "ryu+giga-sushi@aizubange.fukushima.jp",
        "ryu+giga-sushi@aizubange.fukushima.jp",
    ),
    ("Raoul chirurgiens-dentistes.fr", "Raoul chirurgiens-dentistes.fr", ""),
    (
        " Raoul O'hara  <!@historicalsociety.museum>",
        "Raoul O'hara",
        "!@historicalsociety.museum",
    ),
    (
        "Raoul Grosbedon <raoul@CHIRURGIENS-dentistes.fr> ",
        "Raoul Grosbedon",
        "raoul@chirurgiens-dentistes.fr",
    ),
    (
        "Raoul megaraoul@chirurgiens-dentistes.fr",
        "Raoul",
        "megaraoul@chirurgiens-dentistes.fr",
    ),
]


@tagged("res_partner")
class TestPartner(TransactionCaseWithUserDemo):
    @contextmanager
    def mockPartnerCalls(self):
        _original_create = ResPartner.create
        self._new_partners = self.env["res.partner"]

        def _res_partner_create(model, *args, **kwargs):
            records = _original_create(model, *args, **kwargs)
            self._new_partners += records.sudo()
            return records

        with patch.object(
            ResPartner, "create", autospec=True, side_effect=_res_partner_create
        ):
            yield

    def _check_find_or_create(
        self, test_string, expected_name, expected_email, expected_partner=False
    ):
        with self.mockPartnerCalls():
            partner = self.env["res.partner"].get_or_create(test_string)
        if expected_partner:
            self.assertEqual(
                partner,
                expected_partner,
                f"Should have found {expected_partner.name} ({expected_partner.id}), found {partner.name} ({partner.id}) instead",
            )
            self.assertFalse(self._new_partners)
        else:
            self.assertEqual(
                partner,
                self._new_partners,
                f"Should have created a partner, found {partner.name} ({partner.id}) instead",
            )
        self.assertEqual(partner.name, expected_name)
        self.assertEqual(partner.email or "", expected_email)
        return partner

    def test_archive_internal_partners(self):
        test_partner = self.env["res.partner"].create({"name": "test partner"})
        test_user = self.env["res.users"].create(
            {
                "login": "test@odoo.com",
                "partner_id": test_partner.id,
            }
        )
        with self.assertRaises(RedirectWarning):
            test_partner.with_user(self.env.ref("base.user_admin")).action_archive()
        with self.assertRaises(ValidationError):
            test_partner.with_user(self.user_demo).action_archive()

        test_user.action_archive()
        self.assertTrue(
            test_partner.active, "Parter related to user should remain active"
        )

        test_partner.action_archive()

        test_user.action_unarchive()
        self.assertTrue(
            test_partner.active, "Activating user must active related partner"
        )

    def test_barcode_unicity(self):
        Partner = self.env["res.partner"]
        Partner.create({"name": "Barcode A", "barcode": "BARCODE-DUP"})
        with self.assertRaises(ValidationError):
            Partner.create({"name": "Barcode B", "barcode": "BARCODE-DUP"})
        with self.assertRaises(ValidationError):
            Partner.create(
                [
                    {"name": "Barcode C", "barcode": "BARCODE-BATCH"},
                    {"name": "Barcode D", "barcode": "BARCODE-BATCH"},
                ]
            )
        Partner.create({"name": "Barcode E", "barcode": "BARCODE-OTHER"})
        company_b = self.env["res.company"].create({"name": "Barcode Co"})
        Partner.with_company(company_b).create(
            {"name": "Barcode F", "barcode": "BARCODE-DUP"}
        )

    def test_display_name_show_address_follows_address_write(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Movers Inc",
                "street": "1 Old Street",
                "city": "Oldtown",
                "country_id": self.env.ref("base.us").id,
            }
        )
        shown = partner.with_context(show_address=True)
        self.assertIn("1 Old Street", shown.display_name)
        partner.street = "42 New Street"
        self.assertIn("42 New Street", shown.display_name)
        self.assertNotIn("1 Old Street", shown.display_name)
        partner.write({"city": "Newtown", "zip": "99999"})
        self.assertIn("Newtown", shown.display_name)
        self.assertIn("99999", shown.display_name)

    def test_default_get_company_only_when_requested(self):
        parent = self.env["res.partner"].create(
            {"name": "Default Parent", "company_id": self.env.company.id}
        )
        Partner = self.env["res.partner"].with_context(default_parent_id=parent.id)

        values = Partner.default_get(["parent_id", "company_id"])
        self.assertEqual(values.get("company_id"), self.env.company.id)

        values = Partner.default_get(["parent_id"])
        self.assertNotIn("company_id", values)

    def test_email_formatted(self):
        new_partners = self.env["res.partner"].create(
            [
                {
                    "name": "Vlad the Impaler",
                    "email": f"vlad.the.impaler.{idx:02d}@example.com",
                }
                for idx in range(2)
            ]
        )
        self.assertEqual(
            sorted(new_partners.mapped("email_formatted")),
            sorted(
                [
                    f'"Vlad the Impaler" <vlad.the.impaler.{idx:02d}@example.com>'
                    for idx in range(2)
                ]
            ),
            'Email formatted should be "name" <email>',
        )

        for source, (exp_name, exp_email, exp_email_formatted) in [
            (
                "Balázs <vlad.the.negociator@example.com>, vlad.the.impaler@example.com",
                (
                    "Balázs",
                    "vlad.the.negociator@example.com",
                    '"Balázs" <vlad.the.negociator@example.com>',
                ),
            ),
            (
                "Balázs <vlad.the.impaler@example.com>",
                (
                    "Balázs",
                    "vlad.the.impaler@example.com",
                    '"Balázs" <vlad.the.impaler@example.com>',
                ),
            ),
        ]:
            with self.subTest(source=source):
                new_partner_id = self.env["res.partner"].name_create(source)[0]
                new_partner = self.env["res.partner"].browse(new_partner_id)
                self.assertEqual(new_partner.name, exp_name)
                self.assertEqual(new_partner.email, exp_email)
                self.assertEqual(
                    new_partner.email_formatted,
                    exp_email_formatted,
                    "Name_create should take first found email",
                )

        for source, exp_email_formatted, exp_addr in [
            (
                "Vlad the Impaler",
                '"Vlad the Impaler" <vlad.the.impaler@example.com>',
                ["vlad.the.impaler@example.com"],
            ),
            (
                "Balázs",
                '"Balázs" <vlad.the.impaler@example.com>',
                ["vlad.the.impaler@example.com"],
            ),
            (
                "Bike@Home",
                '"Bike@Home" <vlad.the.impaler@example.com>',
                ["Bike@Home", "vlad.the.impaler@example.com"],
            ),
            (
                "Bike @ Home@Home",
                '"Bike @ Home@Home" <vlad.the.impaler@example.com>',
                ["Home@Home", "vlad.the.impaler@example.com"],
            ),
            (
                "Balázs <email.in.name@example.com>",
                '"Balázs <email.in.name@example.com>" <vlad.the.impaler@example.com>',
                ["email.in.name@example.com", "vlad.the.impaler@example.com"],
            ),
        ]:
            with self.subTest(source=source):
                new_partner.write({"name": source})
                self.assertEqual(new_partner.email_formatted, exp_email_formatted)
                self.assertEqual(
                    extract_rfc2822_addresses(new_partner.email_formatted),
                    exp_addr,
                )

        new_partner.write({"name": "Balázs"})
        for source, exp_email_formatted in [
            (
                "Vlad the Impaler <vlad.the.impaler@example.com>",
                '"Balázs" <vlad.the.impaler@example.com>',
            ),
            ('"Balázs" <balazs@adam.hu>', '"Balázs" <balazs@adam.hu>'),
            (
                "vlad.the.impaler@example.com, vlad.the.dragon@example.com",
                '"Balázs" <vlad.the.impaler@example.com,vlad.the.dragon@example.com>',
            ),
            (
                "vlad.the.impaler.com, vlad.the.dragon@example.com",
                '"Balázs" <vlad.the.dragon@example.com>',
            ),
            (
                'vlad.the.impaler.com, "Vlad the Dragon" <vlad.the.dragon@example.com>',
                '"Balázs" <vlad.the.dragon@example.com>',
            ),
            (False, False),
            ("", False),
            (" ", False),
            ("notanemail", False),
        ]:
            with self.subTest(source=source):
                new_partner.write({"email": source})
                self.assertEqual(new_partner.email_formatted, exp_email_formatted)

    def test_find_or_create(self):
        original_partner = self.env["res.partner"].browse(
            self.env["res.partner"].name_create(SAMPLES[0][0])[0]
        )
        all_partners = []

        for (
            (text_input, expected_name, expected_email),
            expected_partner,
            find_idx,
        ) in zip(
            SAMPLES,
            [
                original_partner,
                False,
                False,
                False,
                original_partner,
                False,
                False,
                False,
                False,
                False,
            ],
            [0, 0, 0, 0, 0, 0, 0, 6, 0, 0],
            strict=False,
        ):
            with self.subTest(text_input=text_input):
                if not expected_partner and find_idx:
                    expected_partner = all_partners[find_idx]
                all_partners.append(
                    self._check_find_or_create(
                        text_input,
                        expected_name,
                        expected_email,
                        expected_partner=expected_partner,
                    )
                )

    def test_find_or_create_escapes_ilike_wildcards(self):
        Partner = self.env["res.partner"]
        existing = Partner.create({"name": "AxB", "email": "axb@example.com"})
        found = Partner.get_or_create("a_b@example.com")
        self.assertNotEqual(found, existing)
        self.assertEqual(found.email, "a_b@example.com")
        self.assertEqual(Partner.get_or_create("axb@example.com"), existing)

    def test_is_public(self):
        self.assertFalse(self.env.ref("base.public_user").active)
        self.assertFalse(self.env.ref("base.public_partner").active)
        self.assertTrue(self.env.ref("base.public_partner").is_public)

    def test_lang_computation_code(self):
        default_lang_info = self.env["res.lang"].get_installed()[0]
        default_lang_code = default_lang_info[0]
        self.assertNotEqual(default_lang_code, "de_DE")
        self.assertNotEqual(default_lang_code, "fr_FR")

        partner = self.env["res.partner"].create({"name": "Test Company"})
        self.assertEqual(partner.lang, default_lang_code)

        child = self.env["res.partner"].create(
            {"name": "First Child", "parent_id": partner.id}
        )
        self.assertEqual(child.lang, default_lang_code)

        self.env["res.lang"]._activate_lang("de_DE")
        self.env["res.lang"]._activate_lang("fr_FR")

        partner = (
            self.env["res.partner"]
            .with_context(default_lang="de_DE")
            .create({"name": "Test Company"})
        )
        self.assertEqual(partner.lang, "de_DE")
        first_child = self.env["res.partner"].create(
            {"name": "First Child", "parent_id": partner.id}
        )
        partner.write({"lang": "fr_FR"})
        second_child = self.env["res.partner"].create(
            {"name": "Second Child", "parent_id": partner.id}
        )

        self.assertEqual(partner.lang, "fr_FR")
        self.assertEqual(first_child.lang, "de_DE")
        self.assertEqual(second_child.lang, "fr_FR")

    def test_re_parenting_keeps_an_explicit_lang_and_fills_a_missing_one(self):
        self.env["res.lang"]._activate_lang("de_DE")
        self.env["res.lang"]._activate_lang("fr_FR")
        Partner = self.env["res.partner"]
        parent = Partner.create({"name": "Lang Parent", "lang": "de_DE"})
        explicit = Partner.create({"name": "Explicit Lang", "lang": "fr_FR"})
        blank = Partner.create({"name": "Blank Lang"})
        blank.lang = False
        (explicit | blank).invalidate_recordset()

        explicit.parent_id = parent
        blank.parent_id = parent

        self.assertEqual(
            explicit.lang, "fr_FR", "a re-parent must not overwrite an explicit lang"
        )
        self.assertEqual(
            blank.lang, "de_DE", "a contact without a lang takes its new parent's"
        )

        explicit.write({"parent_id": False, "lang": "de_DE"})
        explicit.write({"parent_id": parent.id, "lang": "fr_FR"})
        self.assertEqual(explicit.lang, "fr_FR", "a lang given with the parent wins")

    def test_name_create(self):
        res_partner = self.env["res.partner"]
        for text, expected_name, expected_mail in SAMPLES:
            with self.subTest(text=text):
                partner_id, _dummy = res_partner.name_create(text)
                partner = res_partner.browse(partner_id)
                self.assertEqual(expected_name or expected_mail.lower(), partner.name)
                self.assertEqual(expected_mail.lower() or False, partner.email)

        partner = self.env["res.partner"].browse(
            self.env["res.partner"]
            .with_context(default_email="John.Wick@example.com")
            .name_create('"Raoulette Vachette" <Raoul@Grosbedon.fr>')[0]
        )
        self.assertEqual(partner.name, "Raoulette Vachette")
        self.assertEqual(partner.email, "raoul@grosbedon.fr")

        partner = self.env["res.partner"].browse(
            self.env["res.partner"]
            .with_context(default_email="John.Wick@example.com")
            .name_create("Raoulette Vachette")[0]
        )
        self.assertEqual(partner.name, "Raoulette Vachette")
        self.assertEqual(partner.email, "John.Wick@example.com")

    def test_name_search(self):
        res_partner = self.env["res.partner"]
        sources = [
            ('"A Raoul Grosbedon" <raoul@chirurgiens-dentistes.fr>', False),
            ("B Raoul chirurgiens-dentistes.fr", True),
            ("C Raoul O'hara  <!@historicalsociety.museum>", True),
            ("ryu+giga-Sushi@aizubange.fukushima.jp", True),
        ]
        for name, active in sources:
            _partner_id, _dummy = res_partner.with_context(
                default_active=active
            ).name_create(name)
        partners = res_partner.name_search("Raoul")
        self.assertEqual(
            len(partners), 2, "Incorrect search number result for name_search"
        )
        partners = res_partner.name_search("Raoul", limit=1)
        self.assertEqual(
            len(partners),
            1,
            "Incorrect search number result for name_search with a limit",
        )
        self.assertEqual(
            partners[0][1],
            "B Raoul chirurgiens-dentistes.fr",
            "Incorrect partner returned, should be the first active",
        )

    def test_name_search_with_user(self):
        test_partner = self.env["res.partner"].create({"name": "Vlad the Impaler"})
        test_user = self.env["res.users"].create(
            {
                "name": "Vlad the Impaler",
                "login": "vlad",
                "email": "vlad.the.impaler@example.com",
            }
        )

        ns_res = self.env["res.partner"].name_search("Vlad", operator="ilike")
        self.assertEqual(
            {i[0] for i in ns_res},
            set((test_partner | test_user.partner_id).ids),
        )

        ns_res = self.env["res.partner"].name_search(
            "Vlad", domain=[("user_ids.email", "ilike", "vlad")]
        )
        self.assertEqual({i[0] for i in ns_res}, set(test_user.partner_id.ids))

        public_user = self.env.ref("base.public_user")
        with self.assertRaises(AccessError):
            test_partner.with_user(public_user).check_access("read")
        ns_res = (
            self.env["res.partner"]
            .with_user(public_user)
            .sudo()
            .name_search("Vlad", domain=[("user_ids.email", "ilike", "vlad")])
        )
        self.assertEqual({i[0] for i in ns_res}, set(test_user.partner_id.ids))

    def test_partner_merge_wizard_dst_partner_id(self):
        test_partner = self.env["res.partner"].create({"name": "Radu the Handsome"})
        expected_partner_name = "%s (%s)" % (test_partner.name, test_partner.id)

        partner_merge_wizard = (
            self.env["base.partner.merge.automatic.wizard"]
            .with_context(
                {
                    "partner_show_db_id": True,
                    "default_dst_partner_id": test_partner,
                }
            )
            .new()
        )
        self.assertEqual(
            partner_merge_wizard.dst_partner_id.display_name,
            expected_partner_name,
            "'Destination Contact' name should contain db ID in brackets",
        )

    def test_display_name_translation(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        self.env.ref("base.module_base")._update_translations(["fr_FR"])

        res_partner = self.env["res.partner"]

        parent_contact = res_partner.create(
            {
                "name": "Parent",
                "type": "contact",
            }
        )

        child_contact = res_partner.create(
            {
                "type": "other",
                "parent_id": parent_contact.id,
            }
        )

        self.assertEqual(
            child_contact.with_context(lang="en_US").display_name,
            "Parent, Other",
        )

        self.assertEqual(
            child_contact.with_context(lang="fr_FR").display_name,
            "Parent, Autre",
        )

    def test_main_user_id(self):
        self.assertEqual(
            self.env.ref("base.partner_root").main_user_id,
            self.env.ref("base.user_root"),
        )
        partner = self.env["res.partner"].create({"name": "Test Partner"})
        self.env["res.users"].create(
            {
                "active": False,
                "login": "archived_user",
                "partner_id": partner.id,
            },
        )
        self.assertFalse(partner.main_user_id)
        portal_user = self.env["res.users"].create(
            {
                "group_ids": [Command.set([self.ref("base.group_portal")])],
                "login": "portal_user",
                "partner_id": partner.id,
            },
        )
        self.assertEqual(partner.main_user_id, portal_user)
        internal_user = self.env["res.users"].create(
            {
                "group_ids": [Command.set([self.ref("base.group_user")])],
                "login": "internal_user",
                "partner_id": partner.id,
            },
        )
        self.assertEqual(partner.main_user_id, internal_user)
        self.env["res.users"].create(
            {
                "group_ids": [Command.set([self.ref("base.group_user")])],
                "login": "internal_user_1d_2",
                "partner_id": partner.id,
            },
        )
        self.assertEqual(partner.main_user_id, internal_user)
        self.assertEqual(partner.with_user(portal_user).main_user_id, portal_user)


@tagged("res_partner")
class TestPartnerStoredNameLanguage(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["res.lang"]._activate_lang("fr_FR")
        cls.env["ir.model.fields.selection"].search(
            [
                ("field_id.model", "=", "res.partner"),
                ("field_id.name", "=", "type"),
                ("value", "=", "invoice"),
            ]
        ).with_context(lang="fr_FR").name = "Facture"
        cls.env.invalidate_all()
        cls.parent = cls.env["res.partner"].create({"name": "Acme", "is_company": True})

    def test_complete_name_does_not_store_the_editing_user_language(self):
        address = self.env["res.partner"].create(
            {"parent_id": self.parent.id, "type": "delivery"}
        )
        self.assertEqual(address.complete_name, "Acme, Delivery")

        address_fr = address.with_context(lang="fr_FR")
        address_fr.write({"type": "invoice"})
        self.assertEqual(
            address_fr.complete_name,
            "Acme, Invoice",
            "the stored name stays language-independent, even when a French"
            " environment triggers the recompute",
        )
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT complete_name FROM res_partner WHERE id = %s", (address.id,)
        )
        self.assertEqual(self.env.cr.fetchone()[0], "Acme, Invoice")

    def test_display_name_still_follows_the_reader_language(self):
        address = self.env["res.partner"].create(
            {"parent_id": self.parent.id, "type": "invoice"}
        )
        self.assertEqual(address.display_name, "Acme, Invoice")
        self.assertEqual(
            address.with_context(lang="fr_FR").display_name,
            "Acme, Facture",
            "display_name is per-reader and must stay translated",
        )


@tagged("res_partner")
class TestPartnerWriteContract(TransactionCase):
    def test_create_computes_the_language_before_the_insert(self):
        Partner = self.env["res.partner"]
        parent = Partner.create({"name": "Lang Source", "is_company": True})
        writes = []
        original = type(Partner).write

        def recording_write(records, vals):
            writes.append(dict(vals))
            return original(records, vals)

        self.patch(type(Partner), "write", recording_write)
        children = Partner.create(
            [
                {"name": f"Lang Child {index}", "parent_id": parent.id}
                for index in range(5)
            ]
        )
        self.assertEqual(set(children.mapped("lang")), {parent.lang})
        self.assertFalse(
            [vals for vals in writes if "lang" in vals],
            "a created partner takes its language in the create, not by a write",
        )

    def test_write_does_not_mutate_the_values_it_is_given(self):
        Partner = self.env["res.partner"]
        manager = new_test_user(
            self.env,
            login="write_contract_manager",
            groups="base.group_user,base.group_partner_manager",
        )
        first, second = Partner.with_user(manager).create(
            [{"name": "Reused A"}, {"name": "Reused B"}]
        )
        vals = {"is_company": True, "website": "example.com"}
        expected = dict(vals)

        first.write(vals)
        self.assertEqual(vals, expected, "write() must leave the caller's dict alone")

        second.write(vals)
        self.assertTrue(first.is_company)
        self.assertTrue(second.is_company, "the second write must not lose is_company")
        self.assertEqual(first.website, "http://example.com")
        self.assertEqual(second.website, "http://example.com")

    def test_write_only_runs_the_parent_sync_for_fields_it_syncs(self):
        Partner = self.env["res.partner"]
        parent = Partner.create({"name": "Sync Parent", "is_company": True})
        child = Partner.create(
            {"name": "Sync Child", "parent_id": parent.id, "type": "contact"}
        )

        seen = []
        original = type(Partner)._fields_sync

        def spy(self, values):
            seen.append(set(values))
            return original(self, values)

        self.patch(type(Partner), "_fields_sync", spy)

        child.write({"comment": "<p>note</p>", "function": "CEO", "ref": "123"})
        self.assertEqual(seen, [], "a non-synced write must not run the parent sync")

        child.write({"vat": "BE0477472701"})
        self.assertTrue(seen, "a commercial-field write must still run the sync")
        self.assertTrue(
            all(fields == {"vat"} for fields in seen),
            "the sync must be handed only the changed commercial field",
        )
        self.assertEqual(parent.vat, "BE0477472701", "vat must propagate to the parent")

    def test_create_does_not_mutate_the_values_it_is_given(self):
        Partner = self.env["res.partner"]
        parent = Partner.create({"name": "Mutation Co", "is_company": True})
        vals = {"name": "Mutated", "parent_id": parent.id, "website": "example.org"}
        expected = dict(vals)
        Partner.create([vals])
        self.assertEqual(vals, expected, "create() must leave the caller's dicts alone")

    def test_archiving_is_blocked_for_any_falsy_active_value(self):
        user = new_test_user(
            self.env, login="archive_guard_user", groups="base.group_user"
        )
        partner = user.partner_id
        for value in (False, 0, None):
            with self.subTest(active=value), self.assertRaises(RedirectWarning):
                partner.write({"active": value})
            self.assertTrue(
                partner.active, f"write(active={value!r}) must not archive the partner"
            )

    def test_write_checks_the_backing_users_once_for_the_whole_batch(self):
        Partner = self.env["res.partner"]
        users = self.env["res.users"].create(
            [
                {
                    "name": f"Backing {index}",
                    "login": f"backing_user_{index}",
                    "group_ids": [Command.link(self.env.ref("base.group_user").id)],
                }
                for index in range(5)
            ]
        )
        calls = []
        original = type(self.env["res.users"]).check_access

        def counting_check_access(records, operation):
            calls.append(len(records))
            return original(records, operation)

        partners = Partner.browse(users.partner_id.ids)
        self.env.invalidate_all()
        with patch.object(
            type(self.env["res.users"]), "check_access", counting_check_access
        ):
            partners.write({"comment": "<p>batched</p>"})
        self.assertEqual(
            calls,
            [len(users)],
            "one access check covering every backing user, not one per partner",
        )


@tagged("res_partner")
class TestPartnerValuePropagationRules(TransactionCase):
    def test_an_address_propagates_whole_or_not_at_all(self):
        Partner = self.env["res.partner"]
        company = Partner.create(
            {"name": "Whole Co", "is_company": True, "street": "S", "city": "C"}
        )
        contact = Partner.create(
            {"name": "Whole Contact", "parent_id": company.id, "type": "contact"}
        )
        self.assertEqual((contact.street, contact.city), ("S", "C"))

        contact.write({"street": False})
        self.assertFalse(
            company.street, "a cleared part of a stated address propagates"
        )
        self.assertEqual(company.city, "C")

        contact.write({"city": False})
        self.assertEqual(
            company.city, "C", "a record with no address at all states nothing"
        )

    def test_commercial_fields_propagate_one_by_one(self):
        Partner = self.env["res.partner"]
        company = Partner.create(
            {
                "name": "PerField Co",
                "is_company": True,
                "vat": "V",
                "company_registry": "R",
            }
        )
        contact = Partner.create({"name": "PerField C", "parent_id": company.id})
        self.assertEqual((contact.vat, contact.company_registry), ("V", "R"))

        company.write({"vat": False})
        self.assertEqual(
            contact.company_registry, "R", "the set field still governs its own value"
        )

    def test_the_two_rules_are_reachable_by_name(self):
        Partner = self.env["res.partner"]
        partner = Partner.create({"name": "Rules", "street": "S"})
        whole = partner._prepare_vals_whole_when_any_set(["street", "city"])
        only = partner._prepare_vals_only_when_set(["street", "city"])
        self.assertEqual(whole, {"street": "S", "city": False})
        self.assertEqual(only, {"street": "S"})
        self.assertEqual(
            Partner.create({"name": "Empty"})._prepare_vals_whole_when_any_set(
                ["street", "city"]
            ),
            {},
        )


@tagged("res_partner")
class TestPartnerNameConstraint(TransactionCase):
    def test_a_contact_without_a_name_is_refused_whatever_the_type_column_holds(self):
        Partner = self.env["res.partner"]
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                Partner.create({"type": "contact"})
        with self.assertRaises(Exception):
            with self.cr.savepoint():
                Partner.create({"type": False})
        Partner.create({"type": "invoice"})

    def test_an_invalid_default_type_falls_back_to_the_field_default(self):
        values = (
            self.env["res.partner"]
            .with_context(default_type="not-a-type")
            .default_get(["type"])
        )
        self.assertEqual(
            values["type"],
            "contact",
            "an unusable default must not leave the type unset",
        )


@tagged("res_partner")
class TestPartnerCompanyDependentSync(TransactionCase):
    def _tree_with_barcode_as_a_commercial_field(self, extra_companies):
        Partner = self.env["res.partner"]
        self.env["res.company"].create(
            [{"name": f"Sweep {extra_companies} {i}"} for i in range(extra_companies)]
        )
        company = Partner.create(
            {"name": f"Sweep Co {extra_companies}", "is_company": True}
        )
        contact = Partner.create(
            {"name": f"Sweep C {extra_companies}", "parent_id": company.id}
        )
        self.env.flush_all()
        return contact

    def test_the_sweep_does_not_grow_with_the_number_of_companies(self):
        Partner = self.env["res.partner"]
        commercial_fields = Partner._commercial_fields()
        with (
            patch.object(
                Partner.__class__,
                "_commercial_fields",
                lambda self: commercial_fields + ["barcode"],
            ),
            patch.object(Partner.__class__, "_check_fields"),
        ):
            self.assertEqual(
                Partner._company_dependent_commercial_fields(),
                [
                    fname
                    for fname in commercial_fields + ["barcode"]
                    if Partner._fields[fname].company_dependent
                ],
            )
            costs = []
            for extra in (3, 12):
                contact = self._tree_with_barcode_as_a_commercial_field(extra)
                self.env.invalidate_all()
                before = self.cr.sql_statement_count
                contact.sudo()._sync_company_dependent_commercial_fields()
                self.env.flush_all()
                costs.append(self.cr.sql_statement_count - before)
            self.assertEqual(
                costs[0],
                costs[1],
                "with nothing stored for any company, the sweep must cost the same"
                f" whatever the database holds, got {costs}",
            )

    def test_only_the_companies_holding_a_value_are_visited(self):
        Partner = self.env["res.partner"]
        other = self.env["res.company"].create({"name": "Holder Co"})
        self.env["res.company"].create([{"name": f"Bystander {i}"} for i in range(5)])
        company = Partner.create({"name": "Holder Parent", "is_company": True})
        contact = Partner.create({"name": "Holder Child", "parent_id": company.id})
        self.env.flush_all()

        self.assertFalse(
            contact._get_stored_company_ids(["barcode"]),
            "no company holds a value, so none can be stale",
        )
        company.with_company(other).barcode = "HOLD-1"
        self.env.flush_all()
        self.assertEqual(
            contact._get_stored_company_ids(["barcode"]),
            {other.id},
            "only the company with a stored value is worth visiting",
        )

    def test_bounding_the_sweep_still_propagates_a_real_value(self):
        Partner = self.env["res.partner"]
        commercial_fields = Partner._commercial_fields()
        other = self.env["res.company"].create({"name": "Reach Co"})
        company = Partner.create({"name": "Reach Parent", "is_company": True})
        company.with_company(other).barcode = "REACH-1"
        self.env.flush_all()
        with (
            patch.object(
                Partner.__class__,
                "_commercial_fields",
                lambda self: commercial_fields + ["barcode"],
            ),
            patch.object(Partner.__class__, "_check_fields"),
        ):
            contact = Partner.create({"name": "Reach Child", "parent_id": company.id})
            self.assertEqual(
                contact.with_company(other).barcode,
                "REACH-1",
                "bounding the sweep must not stop a real value from propagating",
            )


@tagged("res_partner")
class TestPartnerDuplicateIdentifiers(TransactionCase):
    def test_same_vat_partner_is_recomputed_when_the_parent_changes(self):
        Partner = self.env["res.partner"]
        first = Partner.create(
            {"name": "Dup One", "is_company": True, "vat": "BE0477472701"}
        )
        Partner.create({"name": "Dup Two", "is_company": True, "vat": "BE0477472701"})
        self.assertTrue(first.same_vat_partner_id)

        parent = Partner.create({"name": "Dup Parent", "is_company": True})
        first.parent_id = parent
        self.assertFalse(
            first.same_vat_partner_id,
            "attaching a parent must retrigger the duplicate compute",
        )

    def test_only_a_slash_marks_a_partner_as_not_subject_to_tax(self):
        Partner = self.env["res.partner"]
        exempt_a = Partner.create({"name": "Exempt A", "is_company": True, "vat": "/"})
        Partner.create({"name": "Exempt B", "is_company": True, "vat": "/"})
        self.assertFalse(
            exempt_a.same_vat_partner_id, "'/' means no tax id, never a duplicate"
        )

        short_a = Partner.create({"name": "Short A", "is_company": True, "vat": "5"})
        Partner.create({"name": "Short B", "is_company": True, "vat": "5"})
        self.assertTrue(
            short_a.same_vat_partner_id,
            "a one-character tax id is a tax id like any other",
        )

    def test_company_registry_duplicates_are_scoped_to_one_country(self):
        Partner = self.env["res.partner"]
        belgium = self.env.ref("base.be")
        france = self.env.ref("base.fr")
        be_partner = Partner.create(
            {
                "name": "Reg BE",
                "is_company": True,
                "country_id": belgium.id,
                "company_registry": "REG123",
            }
        )
        fr_partner = Partner.create(
            {
                "name": "Reg FR",
                "is_company": True,
                "country_id": france.id,
                "company_registry": "REG123",
            }
        )
        self.assertFalse(
            be_partner.same_company_registry_partner_id,
            "the field help promises uniqueness within one country, not across all",
        )
        self.assertFalse(fr_partner.same_company_registry_partner_id)

        be_twin = Partner.create(
            {
                "name": "Reg BE twin",
                "is_company": True,
                "country_id": belgium.id,
                "company_registry": "REG123",
            }
        )
        self.assertEqual(be_twin.same_company_registry_partner_id, be_partner)

    def test_a_same_vat_partner_the_user_cannot_read_is_not_linked(self):
        Partner = self.env["res.partner"]
        company_a, company_b = self.env["res.company"].create(
            [{"name": "Vat Co A"}, {"name": "Vat Co B"}]
        )
        user = new_test_user(
            self.env,
            login="same_vat_reader",
            groups="base.group_user",
            company_id=company_a.id,
            company_ids=[Command.set(company_a.ids)],
        )
        mine = Partner.create(
            {"name": "Vat Mine", "is_company": True, "vat": "BE0477472701"}
        )
        hidden = Partner.create(
            {
                "name": "Vat Hidden",
                "is_company": True,
                "vat": "BE0477472701",
                "company_id": company_b.id,
            }
        )
        self.assertEqual(mine.same_vat_partner_id, hidden)
        self.assertFalse(hidden.with_user(user).has_access("read"))

        self.assertFalse(
            mine.with_user(user).same_vat_partner_id,
            "a duplicate the user cannot read must not be linked to them",
        )


class TestPartnerSimilarNameDuplicates(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        if not cls.env.registry.has_trigram:
            cls.skipTest(cls, "pg_trgm is not available on this database")

    def test_a_misspelt_name_is_offered_as_a_duplicate(self):
        first = self.Partner.create({"name": "Xylo Bakeries Limited"})
        second = self.Partner.create({"name": "Xylo Bakery Limited"})

        self.assertIn(second, first.duplicate_ids)
        self.assertIn(first, second.duplicate_ids)

    def test_an_unrelated_name_is_not_offered(self):
        first = self.Partner.create({"name": "Xylo Bakeries Limited"})
        self.Partner.create({"name": "Quenneville Ironworks"})

        self.assertNotIn("Quenneville Ironworks", first.duplicate_ids.mapped("name"))

    def test_the_count_matches_what_is_offered(self):
        first = self.Partner.create({"name": "Wexford Cabinetry Group"})
        self.Partner.create({"name": "Wexford Cabinetry Groupe"})

        self.assertEqual(first.duplicate_count, len(first.duplicate_ids))
        self.assertTrue(first.duplicate_count)

    def test_an_own_address_is_never_its_parents_duplicate(self):
        company = self.Partner.create({"name": "Kilbride Joinery Ltd"})
        address = self.Partner.create(
            {
                "name": "Kilbride Joinery Ltd",
                "parent_id": company.id,
                "type": "delivery",
            }
        )

        self.assertNotIn(
            address,
            company.duplicate_ids,
            "a contact's own address is not a duplicate of it",
        )

    def test_a_contact_in_another_country_is_not_a_duplicate(self):
        belgium = self.env.ref("base.be")
        france = self.env.ref("base.fr")
        first = self.Partner.create(
            {"name": "Marchetti Textiles SA", "country_id": belgium.id}
        )
        elsewhere = self.Partner.create(
            {"name": "Marchetti Textiles SA", "country_id": france.id}
        )

        self.assertNotIn(elsewhere, first.duplicate_ids)

    def test_an_archived_contact_is_not_offered(self):
        first = self.Partner.create({"name": "Rathmore Glassworks"})
        archived = self.Partner.create({"name": "Rathmore Glassworks"})
        self.assertIn(archived, first.duplicate_ids)

        archived.active = False
        first.invalidate_recordset(["duplicate_ids", "duplicate_count"])

        self.assertNotIn(archived, first.duplicate_ids)

    def test_a_contact_without_a_name_is_not_searched_for(self):
        nameless = self.Partner.new({"name": False})

        self.assertFalse(nameless.duplicate_ids)
        self.assertFalse(nameless.duplicate_count)

    def test_the_action_lists_the_contact_with_its_duplicates(self):
        first = self.Partner.create({"name": "Ballinrobe Creamery"})
        second = self.Partner.create({"name": "Ballinrobe Creameries"})

        action = first.action_view_duplicates()
        listed = self.Partner.search(action["domain"])

        self.assertEqual(action["res_model"], "res.partner")
        self.assertIn(second, listed)
        self.assertIn(
            first,
            listed,
            "merging is done from a list selection, so the record you came "
            "from has to be selectable alongside its duplicates",
        )

    def test_the_offered_list_can_be_merged_from(self):
        keeper = self.Partner.create(
            {"name": "Halloran Cooperage", "email": "halloran@example.test"}
        )
        twin = self.Partner.create(
            {
                "name": "Halloran Cooperages",
                "phone_ids": [Command.create({"number": "+353 1 555 0111"})],
            }
        )
        listed = self.Partner.search(keeper.action_view_duplicates()["domain"])
        self.assertEqual(listed, keeper | twin)

        Wizard = self.env["base.partner.merge.automatic.wizard"].with_context(
            active_model="res.partner", active_ids=listed.ids
        )
        wizard = Wizard.create(
            Wizard.default_get(["state", "partner_ids", "dst_partner_id"])
        )
        self.assertEqual(wizard.partner_ids, listed)
        wizard.action_merge()

        survivors = self.Partner.search(
            [("name", "in", ["Halloran Cooperage", "Halloran Cooperages"])]
        )
        self.assertEqual(len(survivors), 1, "the pair must end as one contact")
        self.assertEqual(survivors.email, "halloran@example.test")
        self.assertEqual(survivors.phone_ids.number, "+353 1 555 0111")

    def test_the_threshold_decides_what_counts_as_alike(self):
        first = self.Partner.create({"name": "Clonakilty Provisions"})
        loose = self.Partner.create({"name": "Clonakilty Provisioners"})
        self.assertIn(loose, first.duplicate_ids)

        self.env["ir.config_parameter"].sudo().set_param(
            "base.partner_name_similarity_threshold", "0.99"
        )
        first.invalidate_recordset(["duplicate_ids", "duplicate_count"])

        self.assertNotIn(
            loose,
            first.duplicate_ids,
            "raising the bar must narrow what is offered",
        )

    def test_the_wizard_and_the_contact_share_one_threshold(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "base.partner_name_similarity_threshold", "0.82"
        )
        wizard = self.env["base.partner.merge.automatic.wizard"].create({})

        self.assertEqual(
            wizard._get_similar_name_threshold(),
            self.Partner._get_similar_name_threshold(),
            "the wizard must not carry a second copy of the threshold",
        )

    def test_a_similar_name_the_user_cannot_read_is_neither_offered_nor_fatal(self):
        company_a, company_b = self.env["res.company"].create(
            [{"name": "Similar Co A"}, {"name": "Similar Co B"}]
        )
        user = new_test_user(
            self.env,
            login="similar_name_reader",
            groups="base.group_user",
            company_id=company_a.id,
            company_ids=[Command.set(company_a.ids)],
        )
        mine = self.Partner.create(
            {"name": "Tullamore Distillery", "company_id": company_a.id}
        )
        twin = self.Partner.create(
            {"name": "Tullamore Distillerie", "company_id": company_a.id}
        )
        hidden = self.Partner.create(
            {"name": "Tullamore Distillers", "company_id": company_b.id}
        )
        self.assertFalse(hidden.with_user(user).has_access("read"))

        offered = mine.with_user(user).duplicate_ids

        self.assertIn(twin, offered)
        self.assertNotIn(hidden, offered)

    def test_the_recall_leaves_the_trigram_threshold_as_it_found_it(self):
        setting = "SELECT current_setting('pg_trgm.similarity_threshold', true)"
        self.cr.execute(setting)
        before = self.cr.fetchone()[0] or "0.3"
        partner = self.Partner.create({"name": "Threshold Bakeries Limited"})
        partner.invalidate_recordset(["duplicate_ids"])
        partner.mapped("duplicate_ids")
        self.cr.execute(setting)
        self.assertEqual(
            self.cr.fetchone()[0],
            before,
            "the recall bar is transaction-scoped and must not leak to the next"
            " `%` query of the same transaction",
        )

    def test_the_recall_does_not_grow_with_the_batch(self):
        def queries_for(size):
            batch = self.Partner.create(
                [{"name": f"Ardmore Foundry {index}"} for index in range(size)]
            )
            batch.invalidate_recordset(["duplicate_ids", "duplicate_count"])
            self.env.flush_all()
            before = self.cr.sql_statement_count
            batch.mapped("duplicate_ids")
            return self.cr.sql_statement_count - before

        queries_for(2)
        self.assertEqual(
            queries_for(2),
            queries_for(12),
            "recall and fetch must be one query each for the whole batch",
        )


@tagged("res_partner", "res_partner_address")
class TestPartnerAddressCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user = new_test_user(
            cls.env,
            email="emp@test.mycompany.com",
            groups="base.group_user,base.group_partner_manager",
            login="employee",
            name="Employee",
            password="employee",
        )

        cls.base_address_fields = {
            "street",
            "street2",
            "zip",
            "city",
            "state_id",
            "country_id",
        }
        cls.test_country_state = cls.env["res.country.state"].create(
            [
                {
                    "code": "OD",
                    "country_id": cls.env.ref("base.be").id,
                    "name": "Odoo Province",
                },
            ]
        )
        cls.test_industries = cls.env["res.partner.industry"].create(
            [
                {"name": "Balto Impersonators"},
                {"name": "Floppy Advisors"},
                {"name": "Both of the above"},
            ]
        )
        (
            cls.test_address_values_cmp,
            cls.test_address_values_2_cmp,
            cls.test_address_values_3_cmp,
        ) = [
            {
                "city": "Ramillies",
                "country_id": cls.env.ref("base.be"),
                "state_id": cls.test_country_state,
                "street": "Test Street",
                "street2": "10 F",
                "zip": "1367",
            },
            {
                "city": "Ramillies 2",
                "country_id": cls.env.ref("base.us"),
                "state_id": cls.env["res.country.state"],
                "street": "Another Street",
                "street2": False,
                "zip": "013670",
            },
            {
                "city": "Totally Not Ramillies",
                "country_id": cls.env.ref("base.be"),
                "state_id": cls.test_country_state,
                "street": "Third Street",
                "street2": "Without number",
                "zip": "1367#Corgi",
            },
        ]
        (
            cls.test_address_values,
            cls.test_address_values_2,
            cls.test_address_values_3,
        ) = [
            {
                fname: value.id if isinstance(value, models.Model) else value
                for fname, value in values.items()
            }
            for values in (
                cls.test_address_values_cmp,
                cls.test_address_values_2_cmp,
                cls.test_address_values_3_cmp,
            )
        ]

        cls.test_parent = cls.env["res.partner"].create(
            {
                "company_registry": "0477472701",
                "email": "info@ghoststep.com",
                "industry_ids": cls.test_industries[0].ids,
                "is_company": True,
                "name": "GhostStep",
                "phone_ids": [Command.create({"number": "+32455001122"})],
                "vat": "BE0477472701",
                "type": "contact",
                **cls.test_address_values,
            }
        )
        cls.existing = cls.env["res.partner"].create(
            {
                "name": "Existing Contact",
                "parent_id": cls.test_parent.id,
            }
        )

    @users("employee")
    def test_address(self):
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(self.existing[fname], fvalue)

        ct1 = self.env["res.partner"].browse(
            self.env["res.partner"].name_create(
                "Denis Bladesmith <denis.bladesmith@ghoststep.com>"
            )[0]
        )
        self.assertEqual(ct1.type, "contact", 'Default type must be "contact"')

        ct2, inv, deli, other = self.env["res.partner"].create(
            [
                {
                    "name": "Address, Future Sibling of P1",
                    **self.test_address_values_3,
                },
                {
                    "name": "Invoice Child",
                    "street": "Invoice Child Street",
                    "type": "invoice",
                },
                {
                    "name": "Delivery Child",
                    "street": "Delivery Child Street",
                    "type": "delivery",
                },
                {
                    "name": "Other Child",
                    "street": "Other Child Street",
                    "type": "other",
                },
            ]
        )
        ct1_1, inv_1 = self.env["res.partner"].create(
            [
                {
                    "name": "Address, Child of P1",
                    "parent_id": ct1.id,
                },
                {
                    "name": "Address, Child of Invoice",
                    "parent_id": inv.id,
                },
            ]
        )
        for fname in self.base_address_fields:
            self.assertFalse(ct1_1[fname])
        self.assertFalse(ct1_1.vat)
        self.assertEqual(
            inv_1.street, "Invoice Child Street", "Should take parent address"
        )
        self.assertFalse(inv_1.vat)
        inv_2 = (
            (ct1_1 | inv_1)
            .with_context(default_parent_id=inv.id)
            .create(
                {
                    "name": "Address, Child of Invoice",
                }
            )
        )
        self.assertEqual(
            inv_2.street, "Invoice Child Street", "Should take parent address"
        )
        self.assertFalse(inv_2.vat)

        ct1_phone = "+320455999999"
        ct1.write(
            {
                "phone_ids": [Command.create({"number": ct1_phone})],
                "parent_id": self.test_parent.id,
            }
        )
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(ct1[fname], fvalue)
            self.assertFalse(
                ct1_1[fname],
                "Descendants are not updated, only direct children",
            )
        self.assertEqual(
            ct1.email,
            "denis.bladesmith@ghoststep.com",
            "Email should be preserved after sync",
        )
        self.assertEqual(
            ct1.phone_ids.number,
            ct1_phone,
            "Phone should be preserved after address sync",
        )
        self.assertEqual(
            ct1.type, "contact", "Type should be preserved after address sync"
        )
        self.assertEqual(ct1.vat, "BE0477472701", "VAT should come from parent")
        self.assertEqual(
            ct1.industry_ids,
            self.test_industries[0],
            "Industry should come from parent",
        )
        self.assertEqual(
            ct1.company_registry,
            "0477472701",
            "Company registry should come from parent",
        )

        ct1_street = "Different street, 42"
        ct1.write(
            {
                "street": ct1_street,
                "state_id": False,
                "type": "invoice",
            }
        )
        self.assertEqual(
            ct1.street,
            ct1_street,
            "Address fields must not be synced after turning sync off",
        )
        self.assertEqual(
            ct1.zip,
            "1367",
            "Address fields not changed in write should have kept their value",
        )
        for fname in self.base_address_fields:
            if fname == "street":
                self.assertEqual(ct1_1[fname], ct1_street)
            else:
                self.assertFalse(ct1_1[fname])
        self.assertEqual(ct1.type, "invoice")
        self.assertEqual(
            ct1.parent_id,
            self.test_parent,
            "Changing address should not break hierarchy",
        )
        self.assertNotEqual(
            self.test_parent.street,
            ct1_street,
            "Parent address must not be touched",
        )

        ct1.write({"type": "contact"})
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(ct1[fname], fvalue)
            if fname == "street":
                self.assertEqual(ct1_1[fname], ct1_street)
            else:
                self.assertFalse(ct1_1[fname])
        self.assertEqual(
            ct1.type, "contact", "Type should be preserved after address sync"
        )

        ct2.write({"parent_id": self.test_parent.id})
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(ct2[fname], fvalue)

        self.test_parent.write(self.test_address_values_2)
        for fname, fvalue in self.test_address_values_2_cmp.items():
            self.assertEqual(ct1[fname], fvalue)
            self.assertEqual(ct2[fname], fvalue)
            self.assertEqual(self.existing[fname], fvalue)
        for fname in self.base_address_fields:
            if fname == "street":
                self.assertEqual(
                    ct1_1[fname],
                    ct1_street,
                    "Updated only through P1 direct update",
                )
            else:
                self.assertFalse(
                    ct1_1[fname],
                    "Still holding base creation values, no descendants update",
                )
        for child in inv, deli, other:
            self.assertEqual(
                child.street, f"{child.name} Street", "Should not be updated"
            )

        ct1.write(self.test_address_values_3)
        for fname, fvalue in self.test_address_values_3_cmp.items():
            self.assertEqual(self.test_parent[fname], fvalue)
            self.assertEqual(ct1[fname], fvalue)
            self.assertEqual(ct1_1[fname], fvalue)
            self.assertEqual(ct2[fname], fvalue)

    @users("employee")
    def test_address_first_contact_sync(self):
        (
            void_parent_ct,
            void_parent_comp,
            full_parent_ct,
            full_parent_comp,
            void_parent_withparent,
            full_parent_withparent,
        ) = self.env["res.partner"].create(
            [
                {
                    "name": "Void Ct",
                    "is_company": False,
                },
                {
                    "name": "Void Comp",
                    "is_company": True,
                },
                {
                    "name": "Full Ct",
                    "is_company": False,
                    **self.test_address_values_2,
                },
                {
                    "name": "Full Comp",
                    "is_company": False,
                    **self.test_address_values_2,
                },
                {
                    "name": "Void Ct With Parent",
                    "parent_id": self.test_parent.id,
                },
                {
                    "name": "Full Ct With Parent",
                    "parent_id": self.test_parent.id,
                    **self.test_address_values_2,
                },
            ]
        )
        for parent in (
            void_parent_ct + void_parent_comp + full_parent_ct + full_parent_comp
        ):
            with self.subTest(parent_name=parent.name):
                p1 = self.env["res.partner"].create(
                    dict(
                        {
                            "name": "Micheline Brutijus",
                            "parent_id": parent.id,
                        },
                        **self.test_address_values_3,
                    )
                )
                self.assertEqual(
                    p1.type,
                    "contact",
                    'Default type must be "contact", not the copied parent type',
                )
                if parent in (void_parent_ct, void_parent_comp):
                    for fname, fvalue in self.test_address_values_3_cmp.items():
                        self.assertEqual(p1[fname], fvalue, "Creation value taken")
                        self.assertEqual(
                            parent[fname],
                            fvalue,
                            "Should sync void parent to first contact",
                        )
                elif parent in (full_parent_ct, full_parent_comp):
                    for fname, fvalue in self.test_address_values_2_cmp.items():
                        self.assertEqual(
                            p1[fname],
                            fvalue,
                            "Parent wins over creation values",
                        )
                        self.assertEqual(
                            parent[fname],
                            fvalue,
                            "Should not sync parent with address to first contact",
                        )
                elif parent == full_parent_withparent:
                    for fname, fvalue in self.test_address_values_cmp.items():
                        self.assertEqual(p1[fname], fvalue)
                        self.assertEqual(
                            parent[fname],
                            fvalue,
                            "Should not sync parent that is not root to first contact",
                        )
                elif parent == void_parent_withparent:
                    for fname, fvalue in self.test_address_values_cmp.items():
                        self.assertEqual(p1[fname], fvalue)
                        self.assertFalse(
                            parent[fname],
                            "Should not sync parent that is not root to first contact, event when void",
                        )

    def test_address_get(self):
        res_partner = self.env["res.partner"]
        elmtree = res_partner.browse(res_partner.name_create("Elmtree")[0])
        branch1 = res_partner.create(
            {"name": "Branch 1", "parent_id": elmtree.id, "is_company": True}
        )
        leaf10 = res_partner.create(
            {"name": "Leaf 10", "parent_id": branch1.id, "type": "invoice"}
        )
        branch11 = res_partner.create(
            {"name": "Branch 11", "parent_id": branch1.id, "type": "other"}
        )
        leaf111 = res_partner.create(
            {"name": "Leaf 111", "parent_id": branch11.id, "type": "delivery"}
        )
        branch11.write({"is_company": False})
        branch2 = res_partner.create(
            {"name": "Branch 2", "parent_id": elmtree.id, "is_company": True}
        )
        leaf21 = res_partner.create(
            {"name": "Leaf 21", "parent_id": branch2.id, "type": "delivery"}
        )
        leaf22 = res_partner.create({"name": "Leaf 22", "parent_id": branch2.id})
        leaf23 = res_partner.create(
            {"name": "Leaf 23", "parent_id": branch2.id, "type": "contact"}
        )

        self.assertEqual(
            leaf111.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": leaf111.id,
                "invoice": leaf10.id,
                "contact": branch1.id,
                "other": branch11.id,
            },
            "Invalid address resolution",
        )
        self.assertEqual(
            branch11.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": leaf111.id,
                "invoice": leaf10.id,
                "contact": branch1.id,
                "other": branch11.id,
            },
            "Invalid address resolution",
        )

        self.assertEqual(
            elmtree.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": elmtree.id,
                "invoice": elmtree.id,
                "contact": elmtree.id,
                "other": elmtree.id,
            },
            "Invalid address resolution",
        )

        self.assertEqual(
            branch1.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": leaf111.id,
                "invoice": leaf10.id,
                "contact": branch1.id,
                "other": branch11.id,
            },
            "Invalid address resolution",
        )

        self.assertEqual(
            branch2.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": leaf21.id,
                "invoice": branch2.id,
                "contact": branch2.id,
                "other": branch2.id,
            },
            "Invalid address resolution. Company is the first encountered contact, therefore default for unfound addresses.",
        )

        self.assertEqual(
            leaf21.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": leaf21.id,
                "invoice": branch2.id,
                "contact": branch2.id,
                "other": branch2.id,
            },
            "Invalid address resolution, should scan commercial entity ancestor and its descendants",
        )
        self.assertEqual(
            leaf22.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": leaf21.id,
                "invoice": leaf22.id,
                "contact": leaf22.id,
                "other": leaf22.id,
            },
            "Invalid address resolution, should scan commercial entity ancestor and its descendants",
        )
        self.assertEqual(
            leaf23.address_get(["delivery", "invoice", "contact", "other"]),
            {
                "delivery": leaf21.id,
                "invoice": leaf23.id,
                "contact": leaf23.id,
                "other": leaf23.id,
            },
            "Invalid address resolution, `default` should only override if no partner with specific type exists",
        )

        self.assertEqual(
            elmtree.address_get([]),
            {"contact": elmtree.id},
            "Invalid address resolution, no contact means commercial entity ancestor",
        )
        self.assertEqual(
            leaf111.address_get([]),
            {"contact": branch1.id},
            "Invalid address resolution, no contact means finding contact in ancestors",
        )
        branch11.write({"type": "contact"})
        self.assertEqual(
            leaf111.address_get([]),
            {"contact": branch11.id},
            "Invalid address resolution, branch11 should now be contact",
        )

    @users("employee")
    def test_address_parent_company_creation(self):
        sync_commercial_fields = self.env["res.partner"]._synced_commercial_fields()

        individual = self.env["res.partner"].create(
            {
                "industry_ids": self.test_industries[0].ids,
                "is_company": False,
                "name": "Individual",
                "ref": "REFINDIVIDUAL",
                "vat": "BEINDIVIDUAL",
                **self.test_address_values,
            }
        )
        self.assertFalse(individual.is_company)
        self.assertEqual(individual.type, "contact")
        self.assertEqual(individual.ref, "REFINDIVIDUAL")
        self.assertEqual(individual.vat, "BEINDIVIDUAL")
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(individual[fname], fvalue)

        company = self.env["res.partner"].create(
            {
                "is_company": True,
                "name": "Company",
                "ref": "COMPANYREF",
            }
        )
        with patch.object(
            self.env["res.partner"].__class__,
            "_synced_commercial_fields",
            lambda self: sync_commercial_fields + ["ref"],
        ):
            individual.write({"parent_id": company})
        self.assertFalse(
            company.industry_ids, "Industry is not considered for upstream"
        )
        self.assertEqual(company.ref, "COMPANYREF", "not updated from contact child")
        self.assertEqual(company.vat, "BEINDIVIDUAL")
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(
                company[fname],
                fvalue,
                "Void parent should have been updated when adding a contact with address",
            )
            self.assertEqual(
                individual[fname],
                fvalue,
                "Setting parent with void address should not reset child",
            )
        self.assertEqual(
            individual.industry_ids,
            self.test_industries[0],
            "No upstream sync, but no reset either",
        )
        self.assertEqual(individual.ref, "COMPANYREF", "downstream update")
        self.assertEqual(individual.vat, "BEINDIVIDUAL")

    def test_commercial_partner_nullcompany(self):
        P = self.env["res.partner"]
        p0 = P.create({"name": "0", "email": "0"})
        self.assertEqual(
            p0.commercial_partner_id,
            p0,
            "partner without a parent is their own commercial partner",
        )

        p1 = P.create({"name": "1", "email": "1", "parent_id": p0.id})
        self.assertEqual(
            p1.commercial_partner_id,
            p0,
            "partner's parent is their commercial partner",
        )
        p12 = P.create({"name": "12", "email": "12", "parent_id": p1.id})
        self.assertEqual(
            p12.commercial_partner_id,
            p0,
            "partner's GP is their commercial partner",
        )

        p2 = P.create(
            {"name": "2", "email": "2", "parent_id": p0.id, "is_company": True}
        )
        self.assertEqual(
            p2.commercial_partner_id,
            p2,
            "partner flagged as company is their own commercial partner",
        )
        p21 = P.create({"name": "21", "email": "21", "parent_id": p2.id})
        self.assertEqual(
            p21.commercial_partner_id,
            p2,
            "commercial partner is closest ancestor with themselves as commercial partner",
        )

        p3 = P.create({"name": "3", "email": "3", "is_company": True})
        self.assertEqual(
            p3.commercial_partner_id,
            p3,
            "being both parent-less and company should be the same as either",
        )

        notcompanies = p0 | p1 | p12 | p21
        self.env.cr.execute(
            "update res_partner set is_company=null where id = any(%s)",
            [notcompanies.ids],
        )
        for parent in notcompanies:
            p = P.create(
                {
                    "name": parent.name + "_sub",
                    "email": parent.email + "_sub",
                    "parent_id": parent.id,
                }
            )
            self.assertEqual(
                p.commercial_partner_id,
                parent.commercial_partner_id,
                "check that is_company=null is properly handled when looking for ancestor",
            )

    def test_commercial_field_sync(self):
        company_1, company_2 = self.env["res.partner"].create(
            [
                {
                    "company_registry": "123456789",
                    "industry_ids": self.test_industries[0].ids,
                    "is_company": True,
                    "name": "company 1",
                    "vat": "BE013456789",
                },
                {
                    "company_registry": "9876543210",
                    "industry_ids": self.test_industries[0].ids,
                    "is_company": True,
                    "name": "company 2",
                    "vat": "BE9876543210",
                },
            ]
        )

        contact = self.env["res.partner"].create(
            {"name": "someone", "is_company": False, "parent_id": company_1.id}
        )
        self.assertEqual(
            contact.commercial_partner_id,
            company_1,
            "Commercial partner should be recomputed",
        )
        for fname in ("company_registry", "industry_ids", "vat"):
            self.assertEqual(
                contact[fname],
                company_1[fname],
                "Commercial field should be inherited from the company 1",
            )

        contact_dlr = self.env["res.partner"].create(
            {"name": "somewhere", "type": "delivery", "parent_id": contact.id}
        )
        self.assertEqual(
            contact_dlr.commercial_partner_id,
            company_1,
            "Commercial partner should be recomputed",
        )
        for fname in ("company_registry", "industry_ids", "vat"):
            self.assertEqual(
                contact_dlr[fname],
                company_1[fname],
                "Commercial field should be inherited from the company 1",
            )
        contact_ct = self.env["res.partner"].create(
            {"name": "child someone", "parent_id": contact.id}
        )
        self.assertEqual(
            contact_dlr.commercial_partner_id,
            company_1,
            "Commercial partner should be recomputed",
        )
        for fname in ("company_registry", "industry_ids", "vat"):
            self.assertEqual(
                contact_dlr[fname],
                company_1[fname],
                "Commercial field should be inherited from the company 1",
            )

        contact.write({"parent_id": company_2.id})
        self.assertEqual(
            contact.commercial_partner_id,
            company_2,
            "Commercial partner should be recomputed",
        )
        for fname in ("company_registry", "industry_ids", "vat"):
            self.assertEqual(
                contact[fname],
                company_2[fname],
                "Commercial field should be inherited from the company 2",
            )
        self.assertEqual(
            contact_dlr.commercial_partner_id,
            company_2,
            "Commercial partner should be recomputed on delivery",
        )
        for fname in ("company_registry", "industry_ids", "vat"):
            self.assertEqual(
                contact_dlr[fname],
                company_2[fname],
                "Commecial field should be inherited from the company 2 to delivery",
            )
        self.assertEqual(
            contact_ct.commercial_partner_id,
            company_2,
            "Commercial partner should be recomputed on delivery",
        )
        for fname in ("company_registry", "industry_ids", "vat"):
            self.assertEqual(
                contact_ct[fname],
                company_2[fname],
                "Commecial field should be inherited from the company 2 to delivery",
            )

        company_2.write(
            {
                "child_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Alrik Greenthorn",
                            "email": "agr@sunhelm.com",
                        },
                    )
                ]
            }
        )
        contact2 = self.env["res.partner"].search([("email", "=", "agr@sunhelm.com")])
        for fname in ("company_registry", "industry_ids", "vat"):
            self.assertEqual(
                contact2[fname],
                company_2[fname],
                "Commercial field should be inherited from the company 2",
            )

        company_2.write(
            {
                "company_registry": "new",
                "industry_ids": self.test_industries[1].ids,
                "vat": "BEnew",
            }
        )
        for partner in contact + contact_dlr + contact_ct + contact2:
            for fname, fvalue in (
                ("company_registry", "new"),
                ("industry_ids", self.test_industries[1]),
                ("vat", "BEnew"),
            ):
                self.assertEqual(
                    partner[fname],
                    fvalue,
                    "Commercial field should be updated from the company 2",
                )

        contactvat = "BE445566"
        contact.write({"vat": contactvat})
        for partner in company_2 + contact + contact_dlr + contact_ct + contact2:
            self.assertEqual(
                partner.vat,
                contactvat,
                "Commercial sync works upstream, therefore also for siblings",
            )

        newcontactvat = "BE998877"
        contact.write(
            {
                "parent_id": company_1.id,
                "is_company": True,
                "name": "Sunhelm Subsidiary",
                "vat": newcontactvat,
            }
        )
        self.assertEqual(
            contact.vat,
            newcontactvat,
            "Setting is_company should stop auto-sync of commercial fields",
        )
        self.assertEqual(
            contact.commercial_partner_id,
            contact,
            "Incorrect commercial entity resolution after setting is_company",
        )
        self.assertEqual(contact2.vat, contactvat, "Old sibling untouched")
        self.assertEqual(company_1.vat, "BE013456789", "Should not impact parent")
        self.assertEqual(contact_dlr.vat, newcontactvat, "Promotion propagated")
        self.assertEqual(contact_ct.vat, newcontactvat, "Promotion propagated")

        contact.write({"parent_id": company_2.id})
        self.assertEqual(
            contact.vat,
            newcontactvat,
            "Setting is_company should stop auto-sync of commercial fields",
        )
        self.assertEqual(
            contact.commercial_partner_id,
            contact,
            "Incorrect commercial entity resolution after setting is_company",
        )
        self.assertEqual(company_2.vat, contactvat, "Should not impact parent")
        self.assertEqual(
            contact_dlr.vat, newcontactvat, "Parent company stop auto sync"
        )
        self.assertEqual(contact_ct.vat, newcontactvat, "Parent company stop auto sync")

        sunhelmvat2 = "BE0112233453"
        company_2.write({"vat": sunhelmvat2})
        for partner in (contact, contact_ct, contact_dlr):
            self.assertEqual(
                partner.vat,
                newcontactvat,
                "Setting is_company should stop auto-sync of commercial fields",
            )
        for partner in contact2:
            self.assertEqual(
                partner.vat,
                sunhelmvat2,
                "Commercial fields must be automatically synced",
            )

    def test_commercial_field_sync_reset(self):
        sync_commercial_fields = self.env["res.partner"]._synced_commercial_fields()

        individual = self.env["res.partner"].create(
            {
                "is_company": False,
                "name": "Individual",
                "ref": "REFINDIV",
                "vat": "BEINDIVIDUAL",
                **self.test_address_values,
            }
        )
        self.assertFalse(individual.is_company)
        self.assertEqual(individual.type, "contact")
        self.assertEqual(individual.ref, "REFINDIV")
        self.assertEqual(individual.vat, "BEINDIVIDUAL")
        for fname, fvalue in self.test_address_values_cmp.items():
            self.assertEqual(individual[fname], fvalue)

        company = self.env["res.partner"].create(
            {
                "industry_ids": self.test_industries[1].ids,
                "is_company": True,
                "name": "Company",
                "ref": "REFCOMPANY",
                "vat": "BECOMPANY",
                **self.test_address_values_2,
            }
        )
        with patch.object(
            self.env["res.partner"].__class__,
            "_synced_commercial_fields",
            lambda self: sync_commercial_fields + ["ref"],
        ):
            individual.write({"parent_id": company})
        for fname, fvalue in self.test_address_values_2_cmp.items():
            self.assertEqual(
                company[fname], fvalue, "Parent address should have been kept"
            )
        self.assertEqual(
            company.industry_ids,
            self.test_industries[1],
            "Parent commercial field industry should have been kept",
        )
        self.assertEqual(
            company.ref,
            "REFCOMPANY",
            "Parent commercial field VAT should have been kept",
        )
        self.assertEqual(
            company.vat,
            "BECOMPANY",
            "Parent commercial field VAT should have been kept",
        )
        for fname, fvalue in self.test_address_values_2_cmp.items():
            self.assertEqual(
                individual[fname],
                fvalue,
                "Setting parent with an address should force contact address, even if set previously",
            )
        self.assertEqual(
            individual.industry_ids,
            self.test_industries[1],
            "Commercial fields should be synced from parent",
        )
        self.assertEqual(
            individual.ref,
            "REFCOMPANY",
            "Commercial fields should be synced from parent",
        )
        self.assertEqual(
            individual.vat,
            "BECOMPANY",
            "Commercial fields should be synced from parent",
        )

        with patch.object(
            self.env["res.partner"].__class__,
            "_synced_commercial_fields",
            lambda self: sync_commercial_fields + ["ref"],
        ):
            company.write(
                {
                    "industry_ids": [Command.clear()],
                    "ref": False,
                    "vat": False,
                }
            )
        self.assertFalse(individual.industry_ids)
        self.assertFalse(individual.ref)
        self.assertFalse(individual.vat)

        company.write({"industry_ids": self.test_industries[1].ids, "vat": "BECOMPANY"})
        self.assertEqual(individual.industry_ids, self.test_industries[1])
        self.assertEqual(individual.vat, "BECOMPANY")
        individual.write(
            {
                "industry_ids": [Command.clear()],
                "vat": False,
            }
        )
        self.assertEqual(
            company.industry_ids,
            self.test_industries[1],
            "No upstream support of reset",
        )
        self.assertEqual(company.vat, "BECOMPANY", "No upstream support of reset")
        self.assertFalse(individual.industry_ids)
        self.assertFalse(individual.vat)

    def test_company_dependent_commercial_sync(self):
        ResPartner = self.env["res.partner"]

        company_1, company_2 = self.env["res.company"].create(
            [
                {"name": "company_1"},
                {"name": "company_2"},
            ]
        )

        test_partner_company = ResPartner.create(
            {
                "name": "This company",
                "barcode": "Main Company",
                "is_company": True,
            }
        )
        test_partner_company.with_company(company_1).barcode = "Company 1"
        test_partner_company.with_company(company_2).barcode = "Company 2"

        commercial_fields = ResPartner._commercial_fields()
        with (
            patch.object(
                ResPartner.__class__,
                "_commercial_fields",
                lambda self: commercial_fields + ["barcode"],
            ),
            patch.object(ResPartner.__class__, "_check_fields"),
        ):
            child_address = ResPartner.create(
                {
                    "name": "Contact",
                    "parent_id": test_partner_company.id,
                }
            )
            self.assertEqual(child_address.barcode, "Main Company")
            self.assertEqual(child_address.with_company(company_1).barcode, "Company 1")
            self.assertEqual(child_address.with_company(company_2).barcode, "Company 2")

    def test_company_dependent_commercial_sync_falsy_fields(self):
        ResPartner = self.env["res.partner"]

        alt_company = self.env.company.create({"name": "Alt Company"})
        parent = ResPartner.create(
            {"name": "Parent", "is_company": True, "barcode": False}
        )
        parent.with_company(alt_company).barcode = "BARCODE"

        with (
            patch.object(
                ResPartner.__class__,
                "_commercial_fields",
                lambda self: ["barcode"],
            ),
            patch.object(ResPartner.__class__, "_check_fields"),
        ):
            child = ResPartner.create({"name": "Child", "parent_id": parent.id})
            self.assertFalse(child.barcode)
            self.assertEqual(child.with_company(alt_company).barcode, "BARCODE")

    def test_company_change_propagation(self):
        User = self.env["res.users"]
        Partner = self.env["res.partner"]
        Company = self.env["res.company"]

        company_1 = Company.create({"name": "company_1"})
        company_2 = Company.create({"name": "company_2"})

        test_partner_company = Partner.create({"name": "This company"})
        test_user = User.create(
            {
                "name": "This user",
                "login": "thisu",
                "email": "this.user@example.com",
                "company_id": company_1.id,
                "company_ids": [company_1.id],
            }
        )
        test_user.partner_id.write({"parent_id": test_partner_company.id})

        test_partner_company.write({"company_id": company_1.id})
        self.assertEqual(
            test_user.partner_id.company_id.id,
            company_1.id,
            "The new company_id of the partner company should be propagated to its children",
        )

        test_partner_company.write({"company_id": False})
        self.assertFalse(
            test_user.partner_id.company_id.id,
            "If the company_id is deleted from the partner company, it should be propagated to its children",
        )

        with self.assertRaises(
            UserError,
            msg="You should not be able to update the company_id of the partner company if the linked user of a child partner is not an allowed to be assigned to that company",
        ):
            test_partner_company.write({"company_id": company_2.id})

    def test_a_many2one_in_the_format_prints_its_name(self):
        country = self.env["res.country"].create(
            {
                "name": "Formatland",
                "code": "FL",
                "address_format": "%(street)s, %(state_id)s, %(country_id)s",
            }
        )
        state = self.env["res.country.state"].create(
            {"name": "North", "code": "NO", "country_id": country.id}
        )
        partner = self.env["res.partner"].create(
            {
                "name": "Formatted",
                "street": "1 Main",
                "state_id": state.id,
                "country_id": country.id,
            }
        )
        self.assertEqual(
            partner._display_address(without_company=True),
            "1 Main, North (FL), Formatland",
        )

    def test_display_address_missing_key(self):
        country = self.env["res.country"].create(
            {
                "name": "TestCountry",
                "address_format": "%(city)s %(zip)s",
                "code": "ZV",
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "TestPartner",
                "country_id": country.id,
                "city": "TestCity",
                "zip": "12345",
            }
        )
        before = partner._display_address()
        self.env.cr.execute(
            "UPDATE res_country SET address_format ='%%(city)s %%(zip)s %%(nothing)s' WHERE id=%s",
            [country.id],
        )
        self.env["res.country"].invalidate_model()
        self.assertEqual(before, partner._display_address().strip())

    def test_display_address_malformed_format(self):
        country = self.env["res.country"].create(
            {
                "name": "FallbackLand",
                "address_format": "%(city)s %(zip)s",
                "code": "ZY",
            }
        )
        partner = self.env["res.partner"].create(
            {
                "name": "TestPartner",
                "country_id": country.id,
                "street": "12 Main St",
                "city": "TestCity",
                "zip": "12345",
            }
        )
        self.env.cr.execute(
            "UPDATE res_country SET address_format = '%%(city' WHERE id = %s",
            [country.id],
        )
        self.env["res.country"].invalidate_model()
        res_partner_module._FAILED_ADDRESS_FORMATS.discard("%(city")
        with self.assertLogs(res_partner_module._logger, "WARNING") as capture:
            address = partner._display_address()
        self.assertEqual(address, "12 Main St TestCity 12345 FallbackLand")
        self.assertIn("FallbackLand", capture.output[0])
        with self.assertNoLogs(res_partner_module._logger, "WARNING"):
            partner._display_address()

    def test_display_name(self):
        test_partner_jetha = self.env["res.partner"].create(
            {
                "name": "Jethala",
                "street": "Powder gali",
                "street2": "Gokuldham Society",
            }
        )
        test_partner_bhide = self.env["res.partner"].create({"name": "Atmaram Bhide"})

        res_jetha = test_partner_jetha.with_context(show_address=1).display_name
        self.assertEqual(
            res_jetha,
            "Jethala\nPowder gali\nGokuldham Society",
            "name should contain comma separated name and address",
        )
        res_bhide = test_partner_bhide.with_context(show_address=1).display_name
        self.assertEqual(
            res_bhide,
            "Atmaram Bhide",
            "name should contain only name if address is not available, without extra commas",
        )

        test_partner_invoice = self.env["res.partner"].create(
            {"parent_id": self.test_parent.id, "type": "invoice"}
        )
        self.assertEqual(
            test_partner_invoice.with_context(formatted_display_name=True).display_name,
            "GhostStep \t --Invoice--",
            "Formatted display name should show parent name and type when child contact has no name",
        )

    def test_display_name_hide_company_context(self):
        company = self.env["res.partner"].create(
            {"name": "Sesame Inc", "is_company": True}
        )
        contact = self.env["res.partner"].create(
            {"name": "Elmo", "parent_id": company.id}
        )
        self.assertEqual(contact.display_name, "Sesame Inc, Elmo")
        self.assertEqual(
            contact.with_context(partner_display_name_hide_company=True).display_name,
            "Elmo",
            "Context key must hide the parent company in display_name",
        )
        self.assertEqual(
            contact.display_name,
            "Sesame Inc, Elmo",
            "Reading with the context key must not poison the keyless cache",
        )

    def test_accessibility_of_company_partner_from_branch(self):
        company = self.env["res.company"].create({"name": "company"})
        branch = self.env["res.company"].create(
            {"name": "branch", "parent_id": company.id}
        )
        partner = self.env["res.partner"].create(
            {"name": "partner", "company_id": company.id}
        )
        user = self.env["res.users"].create(
            {
                "name": "user",
                "login": "user",
                "company_id": branch.id,
                "company_ids": [branch.id],
            }
        )
        record = (
            self.env["res.partner"].with_user(user).search([("id", "=", partner.id)])
        )
        self.assertEqual(record.id, partner.id)

    def test_archived_descendants_follow_the_commercial_and_address_sync(self):
        Partner = self.env["res.partner"]
        company = Partner.create({"name": "Archive Co", "is_company": True})
        active = Partner.create({"name": "Kept", "parent_id": company.id})
        archived = Partner.create({"name": "Gone", "parent_id": company.id})
        grandchild = Partner.create({"name": "Gone Jr", "parent_id": archived.id})
        (archived | grandchild).action_archive()

        company.write({"vat": "BEARCHIVE", "street": "Sync Street"})

        for partner in (active, archived, grandchild):
            self.assertEqual(partner.vat, "BEARCHIVE", partner.name)
        self.assertEqual(archived.street, "Sync Street")

    def test_a_batch_commercial_write_syncs_the_children_in_one_pass(self):
        Partner = self.env["res.partner"]

        def queries_for(size):
            companies = Partner.create(
                [
                    {"name": f"Batch Co {index}", "is_company": True}
                    for index in range(size)
                ]
            )
            Partner.create(
                [
                    {"name": f"Batch Kid {index}", "parent_id": company.id}
                    for index, company in enumerate(companies)
                ]
            )
            self.env.flush_all()
            self.env.invalidate_all()
            before = self.cr.sql_statement_count
            companies.write({"vat": f"BEBATCH{size}"})
            self.env.flush_all()
            return self.cr.sql_statement_count - before

        queries_for(2)
        self.assertEqual(
            queries_for(2),
            queries_for(12),
            "the descendants of a batch written the same values sync in one write",
        )

    def test_children_sync_skips_walk_without_commercial_fields(self):
        company = self.env["res.partner"].create(
            {"name": "company", "is_company": True, "vat": "BE013456789"}
        )
        self.env["res.partner"].create(
            {"name": "child", "is_company": False, "parent_id": company.id}
        )
        with patch.object(
            type(company),
            "_sync_commercial_fields_to_descendants",
            autospec=True,
        ) as sync_mock:
            company.write({"ref": "123456"})
        self.assertFalse(
            sync_mock.called,
            "Writing a non-commercial field must not walk the descendant subtree",
        )

        with patch.object(
            type(company),
            "_sync_commercial_fields_to_descendants",
            autospec=True,
        ) as sync_mock:
            company.write({"vat": "BE9876543210"})
        self.assertTrue(
            sync_mock.called,
            "Writing a commercial field must still sync descendants",
        )


@tagged("res_partner", "post_install", "-at_install")
class TestPartnerForm(TransactionCase):
    def test_lang_computation_form_view(self):
        default_lang_code = self.env["ir.default"]._get("res.partner", "lang") or False
        self.assertNotEqual(default_lang_code, "de_DE")
        self.assertNotEqual(default_lang_code, "fr_FR")

        partner_form = Form(self.env["res.partner"], "base.view_partner_form")
        partner_form.name = "Test Company"
        self.assertEqual(
            partner_form.lang,
            default_lang_code,
            "New partner's lang should be default one",
        )
        partner = partner_form.save()
        self.assertEqual(partner.lang, default_lang_code)

        with partner_form.child_ids.new() as child:
            child.name = "First Child"
            self.assertEqual(
                child.lang,
                default_lang_code,
                "Child contact's lang should have the same as its parent",
            )
        partner = partner_form.save()
        self.assertEqual(partner.child_ids.lang, default_lang_code)

        self.env["res.lang"]._activate_lang("de_DE")
        self.env["res.lang"]._activate_lang("fr_FR")

        partner_form = Form(
            self.env["res.partner"].with_context(default_lang="de_DE"),
            "base.view_partner_form",
        )
        partner_form.is_company = True
        partner_form.name = "Test Company"
        self.assertEqual(
            partner_form.lang,
            "de_DE",
            "New partner's lang should take default from context",
        )
        with partner_form.child_ids.new() as child:
            child.name = "First Child"
            self.assertEqual(
                child.lang,
                "de_DE",
                "Child contact's lang should be the same as its parent.",
            )
        partner_form.lang = "fr_FR"
        self.assertEqual(
            partner_form.lang,
            "fr_FR",
            "New partner's lang should take user input",
        )
        with partner_form.child_ids.new() as child:
            child.name = "Second Child"
            self.assertEqual(
                child.lang,
                "fr_FR",
                "Child contact's lang should be the same as its parent.",
            )
        partner = partner_form.save()
        self.assertEqual(partner.child_ids.mapped("lang"), ["de_DE", "fr_FR"])

        self.assertEqual(partner.lang, "fr_FR")
        self.assertEqual(
            partner.child_ids.filtered(lambda p: p.name == "First Child").lang,
            "de_DE",
        )
        self.assertEqual(
            partner.child_ids.filtered(lambda p: p.name == "Second Child").lang,
            "fr_FR",
        )

    def test_onchange_parent_sync_user(self):
        company_1 = self.env["res.company"].create({"name": "company_1"})
        test_user = self.env["res.users"].create(
            {
                "name": "This user",
                "login": "thisu",
                "email": "this.user@example.com",
                "company_id": company_1.id,
                "company_ids": [company_1.id],
            }
        )
        test_parent_partner = self.env["res.partner"].create(
            {
                "is_company": True,
                "name": "Micheline",
                "user_id": test_user.id,
            }
        )
        with Form(self.env["res.partner"]) as partner_form:
            partner_form.parent_id = test_parent_partner
            partner_form.is_company = False
            partner_form.name = "Philip"
            self.assertEqual(partner_form.user_id, test_parent_partner.user_id)


@tagged("res_partner")
class TestPartnerRecursion(TransactionCase):
    def setUp(self):
        super().setUp()
        res_partner = self.env["res.partner"]
        self.p1 = res_partner.browse(res_partner.name_create("Elmtree")[0])
        self.p2 = res_partner.create(
            {"name": "Elmtree Child 1", "parent_id": self.p1.id}
        )
        self.p3 = res_partner.create(
            {"name": "Elmtree Grand-Child 1.1", "parent_id": self.p2.id}
        )

    def test_100_res_partner_recursion(self):
        self.assertFalse(self.p3._has_cycle())
        self.assertFalse((self.p1 + self.p2 + self.p3)._has_cycle())

        self.assertFalse(self.env["res.partner"]._has_cycle())

    def test_101_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p1.write({"parent_id": self.p3.id})

    def test_102_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p2.write({"parent_id": self.p3.id})

    def test_103_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            self.p3.write({"parent_id": self.p3.id})

    def test_104_res_partner_recursion_indirect_cycle(self):
        p3b = self.p1.create(
            {"name": "Elmtree Grand-Child 1.2", "parent_id": self.p2.id}
        )
        with self.assertRaises(ValidationError):
            self.p2.write(
                {
                    "child_ids": [
                        Command.update(self.p3.id, {"parent_id": p3b.id}),
                        Command.update(p3b.id, {"parent_id": self.p3.id}),
                    ]
                }
            )

    def test_105_res_partner_recursion(self):
        with self.assertRaises(ValidationError):
            (self.p3 + self.p1).parent_id = self.p2

    def test_110_res_partner_recursion_multi_update(self):
        ps = self.p1 + self.p2 + self.p3
        self.assertTrue(ps.write({"ref": "123456"}))

    def test_111_res_partner_recursion_infinite_loop(self):
        self.p2.parent_id = False
        self.p3.parent_id = False
        self.p1.parent_id = self.p2
        with self.assertRaises(ValidationError):
            (self.p3 | self.p2).write({"parent_id": self.p1.id})


@tagged("res_partner")
class TestPartnerCategory(TransactionCase):
    def test_name_search(self):
        category = self.env["res.partner.tag"].create({"name": "buggy_test"})
        result = self.env["res.partner.tag"].name_search("buggy_test")
        self.assertEqual(len(result), 1)
        self.assertEqual(result, [(category.id, category.display_name)])

    def test_recursion_rejected(self):
        Category = self.env["res.partner.tag"]
        a = Category.create({"name": "A"})
        b = Category.create({"name": "B", "parent_id": a.id})
        c = Category.create({"name": "C", "parent_id": b.id})
        with self.assertRaises(UserError):
            a.write({"parent_id": c.id})
        with self.assertRaises(UserError):
            a.write({"parent_id": a.id})

    def test_display_name_full_ancestor_path(self):
        Category = self.env["res.partner.tag"]
        a = Category.create({"name": "A"})
        b = Category.create({"name": "B", "parent_id": a.id})
        c = Category.create({"name": "C", "parent_id": b.id})
        self.assertEqual(c.display_name, "A / B / C")
        a.name = ""
        a.invalidate_recordset(["name"])
        c.invalidate_recordset(["display_name"])
        self.assertEqual(c.display_name, " / B / C")

    def test_display_name_new_record_fallback(self):
        Category = self.env["res.partner.tag"]
        parent = Category.create({"name": "Stored Parent"})
        draft = Category.new({"name": "Draft Child", "parent_id": parent.id})
        self.assertEqual(draft.display_name, "Stored Parent / Draft Child")

    def test_display_name_invalidated_on_parent_rename(self):
        Category = self.env["res.partner.tag"]
        a = Category.create({"name": "A"})
        b = Category.create({"name": "B", "parent_id": a.id})
        self.assertEqual(b.display_name, "A / B")
        a.name = "A2"
        self.assertEqual(b.display_name, "A2 / B")

    def test_search_display_name_child_of(self):
        Category = self.env["res.partner.tag"]
        parent = Category.create({"name": "Furniture"})
        child = Category.create({"name": "Chairs", "parent_id": parent.id})
        result = Category.search([("display_name", "like", "Furniture")])
        self.assertIn(parent, result)
        self.assertIn(child, result)
        not_result = Category.search([("display_name", "not like", "Furniture")])
        self.assertNotIn(parent, not_result)
        self.assertNotIn(child, not_result)


class TestPartnerGeolocationInvalidation(TransactionCase):
    """Cover when a partner's stored coordinates survive a write, and when not.

    `partner_latitude` / `partner_longitude` describe where the address on the
    same record is, so the two have to move together. This lived twice in
    addons, in `geocoding` and in `web_map`, before it came here.
    """

    def test_moving_the_address_clears_the_coordinates(self):
        """Check that a write that changes the address drops the position."""
        partner = self.env["res.partner"].create(
            {
                "name": "Moving",
                "street": "Old street",
                "partner_latitude": 5.0,
                "partner_longitude": 6.0,
            }
        )

        partner.write({"street": "New street"})

        self.assertEqual(partner.partner_latitude, 0.0)
        self.assertEqual(partner.partner_longitude, 0.0)

    def test_moving_street2_clears_the_coordinates(self):
        """Check that street2 counts as part of the address.

        It was missing from the list this override checks, so editing the
        second address line moved the partner while leaving its old pin.
        """
        partner = self.env["res.partner"].create(
            {
                "name": "Second Line",
                "street": "Same street",
                "street2": "Old block",
                "partner_latitude": 5.0,
                "partner_longitude": 6.0,
            }
        )

        partner.write({"street2": "New block"})

        self.assertEqual(partner.partner_latitude, 0.0)

    def test_restating_the_same_address_keeps_the_coordinates(self):
        """Check that a write that moves no address part keeps the position.

        A caller replaying a full payload — an import, or an unchanged dict —
        used to discard a geocoding result that was still correct.
        """
        partner = self.env["res.partner"].create(
            {
                "name": "Stationary",
                "street": "Same street",
                "city": "Same city",
                "partner_latitude": 5.0,
                "partner_longitude": 6.0,
            }
        )

        partner.write({"street": "Same street", "city": "Same city"})

        self.assertEqual(partner.partner_latitude, 5.0)
        self.assertEqual(partner.partner_longitude, 6.0)

    def test_a_write_supplying_both_coordinates_keeps_them(self):
        """Check that an address write carrying a new position keeps it."""
        partner = self.env["res.partner"].create(
            {"name": "Relocated", "street": "Old street"}
        )

        partner.write(
            {
                "street": "New street",
                "partner_latitude": 7.0,
                "partner_longitude": 8.0,
            }
        )

        self.assertEqual(partner.partner_latitude, 7.0)
        self.assertEqual(partner.partner_longitude, 8.0)

    def test_a_write_supplying_one_coordinate_clears_both(self):
        """Check that half a position is refused rather than half-applied."""
        partner = self.env["res.partner"].create(
            {
                "name": "Half Located",
                "street": "Old street",
                "partner_latitude": 5.0,
                "partner_longitude": 6.0,
            }
        )

        partner.write({"street": "New street", "partner_latitude": 7.0})

        self.assertEqual(partner.partner_latitude, 0.0)
        self.assertEqual(partner.partner_longitude, 0.0)

    def test_a_write_outside_the_address_keeps_the_coordinates(self):
        """Check that a write touching no address field keeps the position."""
        partner = self.env["res.partner"].create(
            {
                "name": "Renamed",
                "street": "Same street",
                "partner_latitude": 5.0,
                "partner_longitude": 6.0,
            }
        )

        partner.write({"name": "Renamed Again"})

        self.assertEqual(partner.partner_latitude, 5.0)
        self.assertEqual(partner.partner_longitude, 6.0)

    def test_the_reset_does_not_mutate_the_caller_s_values(self):
        """Check that the coordinate reset does not leak into the caller's dict."""
        partner = self.env["res.partner"].create(
            {"name": "Shared vals", "street": "Old street"}
        )
        vals = {"street": "New street"}

        partner.write(vals)

        self.assertEqual(vals, {"street": "New street"})


@tagged("post_install", "-at_install")
class TestPartnerDisplayNameColumn(TransactionCase):
    def test_complete_name_is_the_display_name_without_context(self):
        Partner = self.env["res.partner"].with_context({})
        company = Partner.create({"name": "Column Co", "is_company": True})
        Partner.create(
            {"name": "Named Child", "parent_id": company.id, "type": "contact"}
        )
        Partner.create({"name": False, "parent_id": company.id, "type": "delivery"})
        Partner.create({"name": "Spaced \n Name", "is_company": True})
        self.assertEqual(ResPartner._display_name_column, "complete_name")
        for partner in Partner.search([]):
            self.assertEqual(
                partner.display_name,
                partner.complete_name,
                "with no display context, display_name must be the stored column",
            )
        keyed = company.with_context(
            show_email=True, partner_display_name_hide_company=True
        )
        self.assertTrue(
            set(keyed.env.context) & set(ResPartner._display_name_context_keys),
            "the context keys that change display_name are declared",
        )

    def test_company_display_name_is_code_or_name(self):
        Company = self.env["res.company"].with_context({})
        coded = Company.create({"name": "Coded Co", "code": "CC"})
        plain = Company.create({"name": "Plain Co"})
        self.assertEqual(coded.display_name, "CC")
        self.assertEqual(plain.display_name, "Plain Co")
        self.assertEqual(Company._display_name_column, ("code", "name"))
        for company in Company.search([]):
            self.assertEqual(company.display_name, company.code or company.name)
        self.assertEqual(
            Company._search_display_name("ilike", "Co"),
            Company.with_context(other_key=1)._search_display_name("ilike", "Co"),
        )


@tagged("res_partner")
class TestPartnerImportBatch(TransactionCase):
    def _queries_for_import_of(self, count):
        Partner = self.env["res.partner"]
        parents = Partner.create(
            [{"name": f"IMPB parent {count}-{i}"} for i in range(count)]
        )
        self.env.flush_all()
        self.env.invalidate_all()
        before = self.cr.sql_statement_count
        result = Partner.load(
            ["name", "parent_id"],
            [
                [f"IMPB child {count}-{i}", parent.name]
                for i, parent in enumerate(parents)
            ],
        )
        self.env.flush_all()
        self.assertFalse(result["messages"])
        self.assertEqual(len(result["ids"]), count)
        return self.cr.sql_statement_count - before

    def test_import_query_count_does_not_grow_with_the_number_of_parents(self):
        small = self._queries_for_import_of(10)
        large = self._queries_for_import_of(40)
        self.assertLessEqual(
            large,
            small + 10,
            f"an import of 40 children of 40 parents cost {large} queries against "
            f"{small} for 10: the parents must be fetched once, not once per row",
        )


@tagged("post_install", "-at_install")
class TestPartnerSmallContracts(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Partner = cls.env["res.partner"]
        cls.be = cls.env.ref("base.be")
        cls.gr = cls.env.ref("base.gr")
        cls.us = cls.env.ref("base.us")

    def test_vat_lookup_variants_follow_the_eu_prefix_rule(self):
        cases = [
            (
                {"vat": "BE0477472701", "country_id": self.be.id},
                ["BE0477472701", "0477472701"],
            ),
            (
                {"vat": "0477472701", "country_id": self.be.id},
                ["0477472701", "BE0477472701"],
            ),
            (
                {"vat": "123456", "country_id": self.gr.id},
                ["123456", "GR123456", "EL123456"],
            ),
            ({"vat": "12-3456789", "country_id": self.us.id}, ["12-3456789"]),
            ({"vat": "/", "country_id": self.be.id}, []),
            ({"vat": False, "country_id": self.be.id}, []),
        ]
        for values, expected in cases:
            with self.subTest(values=values):
                partner = self.Partner.new({"name": "Vat", **values})
                self.assertEqual(partner._get_vat_lookup_variants(), expected)

    def test_a_website_without_a_scheme_gets_http(self):
        partner = self.Partner.create({"name": "Web", "website": "example.com/shop"})
        self.assertEqual(partner.website, "http://example.com/shop")
        partner.write({"website": "https://secure.example.com"})
        self.assertEqual(partner.website, "https://secure.example.com")

    def test_a_copy_is_named_as_a_copy_unless_told_otherwise(self):
        partner = self.Partner.create({"name": "Original"})
        self.assertEqual(partner.copy().name, "Original (copy)")
        self.assertEqual(partner.copy({"name": "Renamed"}).name, "Renamed")

    def test_an_import_realigns_a_state_to_the_row_country(self):
        State = self.env["res.country.state"]
        be_state = State.create(
            {"name": "Namur", "code": "ZZ9", "country_id": self.be.id}
        )
        gr_state = State.create(
            {"name": "Namur GR", "code": "ZZ9", "country_id": self.gr.id}
        )
        lonely = State.create(
            {"name": "Nowhere", "code": "NWH", "country_id": self.be.id}
        )
        realigned, dropped = self.Partner.with_context(import_file=True).create(
            [
                {
                    "name": "Realigned",
                    "state_id": be_state.id,
                    "country_id": self.gr.id,
                },
                {"name": "Dropped", "state_id": lonely.id, "country_id": self.gr.id},
            ]
        )
        self.assertEqual(realigned.state_id, gr_state)
        self.assertFalse(dropped.state_id)

    def test_address_get_multi_answers_like_address_get_per_partner(self):
        company = self.Partner.create({"name": "Multi Co", "is_company": True})
        delivery = self.Partner.create(
            {"name": "Dock", "parent_id": company.id, "type": "delivery"}
        )
        contact = self.Partner.create({"name": "Person", "parent_id": company.id})
        loner = self.Partner.create({"name": "Loner"})
        batch = company | contact | loner
        multi = batch._address_get_multi(["delivery", "invoice"])
        for partner in batch:
            self.assertEqual(
                multi[partner.id], partner.address_get(["delivery", "invoice"])
            )
        self.assertEqual(multi[contact.id]["delivery"], delivery.id)
        self.assertEqual(multi[loner.id]["delivery"], loner.id)

    def test_email_formatted_quotes_and_joins(self):
        cases = [
            ("John Doe", "j@example.com", '"John Doe" <j@example.com>'),
            ("Doe, John", "j@example.com", '"Doe, John" <j@example.com>'),
            (
                "Two",
                "a@example.com, b@example.com",
                '"Two" <a@example.com,b@example.com>',
            ),
            ("Broken", "not-an-email", False),
            ("Raw", "raw@localhost", '"Raw" <raw@localhost>'),
        ]
        for name, email, expected in cases:
            with self.subTest(name=name):
                partner = self.Partner.create({"name": name, "email": email})
                self.assertEqual(partner.email_formatted, expected)

    def test_tz_offset_reads_the_zone(self):
        utc = self.Partner.create({"name": "UTC", "tz": "UTC"})
        self.assertEqual(utc.tz_offset, "+0000")
        unset = self.Partner.create({"name": "No zone", "tz": False})
        self.assertEqual(unset.tz_offset, "+0000")

    def test_primary_industry_returns_to_the_first_when_dropped(self):
        Industry = self.env["res.partner.industry"]
        farming, packing = Industry.create([{"name": "Farming"}, {"name": "Packing"}])
        partner = self.Partner.create(
            {"name": "Grower", "industry_ids": [Command.set([farming.id, packing.id])]}
        )
        self.assertEqual(partner.primary_industry_id, farming)
        partner.primary_industry_id = packing
        partner.industry_ids = [Command.unlink(packing.id)]
        self.assertEqual(partner.primary_industry_id, farming)
        partner.industry_ids = [Command.clear()]
        self.assertFalse(partner.primary_industry_id)

    def test_a_parent_created_from_a_name_takes_the_contact_address_and_vat(self):
        contact = self.Partner.create(
            {
                "name": "Ann",
                "vat": "BE0477472701",
                "street": "Rue 1",
                "country_id": self.be.id,
            }
        )
        child = self.Partner.create({"name": "Ann Jr", "parent_id": contact.id})
        parent = contact._create_parent_from_name("Ann Co", {"website": "ann.example"})
        self.assertTrue(parent.is_company)
        self.assertEqual(parent.vat, "BE0477472701")
        self.assertEqual(parent.street, "Rue 1")
        self.assertEqual(parent.website, "http://ann.example")
        self.assertEqual(contact.parent_id, parent)
        self.assertEqual(child.parent_id, parent)
        self.assertFalse(contact._create_parent_from_name(""))
