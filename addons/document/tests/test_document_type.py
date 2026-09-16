import base64
from datetime import date, timedelta

from freezegun import freeze_time
from psycopg import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class DocumentTypeCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.folder = cls.env["document.document"].create(
            {"name": "Type Test Folder", "type": "folder"}
        )

    @classmethod
    def _type(cls, code, **vals):
        return cls.env["document.type"].create(
            {
                "name": f"Type {code}",
                "code": code,
                "company_id": cls.company.id,
                **vals,
            }
        )

    @classmethod
    def _doc(cls, doc_type=None, days=None, **vals):
        if days is not None:
            vals["date_expiration"] = date.today() + timedelta(days=days)
        return cls.env["document.document"].create(
            {
                "name": vals.pop("name", "Typed Doc"),
                "folder_id": cls.folder.id,
                "document_type_id": doc_type.id if doc_type else False,
                **vals,
            }
        )

    def _stored_state(self, doc):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT expiration_state FROM document_document WHERE id = %s", (doc.id,)
        )
        return self.env.cr.fetchone()[0]


class TestDocumentTypeDefaults(DocumentTypeCase):
    def test_defaults(self):
        doc_type = self._type("WP")

        self.assertTrue(doc_type.active)
        self.assertEqual(doc_type.sequence, 10)
        self.assertTrue(doc_type.has_expiration)
        self.assertTrue(doc_type.is_renewable)
        self.assertEqual(doc_type.default_validity_days, 0)

    def test_name_keeps_the_inherited_required_and_translate(self):
        field = self.env["document.type"]._fields["name"]

        self.assertTrue(field.required)
        self.assertTrue(
            field.translate,
            "_name_src_uniq indexes name->>'en_US', so this must stay jsonb",
        )


class TestCodeUniqueness(DocumentTypeCase):
    def _global(self, code):
        return self.env["document.type"].create(
            {
                "name": f"Global {code} {self.env['document.type'].search_count([])}",
                "code": code,
                "company_id": False,
            }
        )

    def test_two_global_types_cannot_share_a_code(self):
        self._global("UNIQ_GLOBAL")
        self.env.flush_all()

        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._global("UNIQ_GLOBAL")
            self.env.flush_all()

    def test_two_types_of_one_company_cannot_share_a_code(self):
        self._type("UNIQ_COMPANY")
        self.env.flush_all()

        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._type("UNIQ_COMPANY")
            self.env.flush_all()

    def test_a_global_and_a_company_type_may_share_a_code(self):
        self._global("UNIQ_MIXED")
        self._type("UNIQ_MIXED")
        self.env.flush_all()

        self.assertEqual(
            self.env["document.type"].search_count([("code", "=", "UNIQ_MIXED")]), 2
        )


class TestExpirationState(DocumentTypeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expiring_type = cls._type("EXP")
        cls.non_expiring_type = cls._type("NOEXP", has_expiration=False)

    def test_states(self):
        cases = (
            (self.expiring_type, 60, "valid", 60),
            (self.expiring_type, 31, "valid", 31),
            (self.expiring_type, 30, "expiring_soon", 30),
            (self.expiring_type, 0, "expiring_soon", 0),
            (self.expiring_type, -1, "expired", -1),
            (self.expiring_type, None, "missing", 0),
            (self.non_expiring_type, None, False, 0),
            (self.non_expiring_type, -10, False, -10),
            (None, 60, False, 60),
            (None, None, False, 0),
        )
        for doc_type, days, expiration, days_left in cases:
            with self.subTest(type=doc_type and doc_type.code, days=days):
                doc = self._doc(doc_type, days)
                self.assertEqual(doc.expiration_state, expiration)
                self.assertEqual(doc.days_left, days_left)

    def test_the_state_follows_the_type(self):
        doc = self._doc(self.expiring_type, -10)
        self.assertEqual(doc.expiration_state, "expired")

        doc.document_type_id = self.non_expiring_type
        self.assertFalse(doc.expiration_state, "the type says the date does not matter")

        doc.document_type_id = self.expiring_type
        self.assertEqual(doc.expiration_state, "expired")

        doc.date_expiration = False
        self.assertEqual(doc.expiration_state, "missing")

    def test_a_document_cannot_carry_another_companys_type(self):
        other = self.env["res.company"].create({"name": "Other Co"})
        foreign_type = self._type("FOREIGN", company_id=other.id)

        with self.assertRaises(ValidationError):
            self._doc(foreign_type, company_id=self.company.id)

    def test_a_global_type_fits_any_company(self):
        global_type = self.env["document.type"].create(
            {"name": "Global", "code": "GLOBAL_OK", "company_id": False}
        )

        self._doc(global_type, company_id=self.company.id)


class TestLegalNumber(DocumentTypeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type = cls._type("LEGAL")

    def test_legal_number_is_unique_per_type_even_without_a_company(self):
        self._doc(self.doc_type, legal_number="LN-1", company_id=False)
        self.env.flush_all()

        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._doc(self.doc_type, legal_number="LN-1", company_id=False)
            self.env.flush_all()

    def test_documents_without_a_legal_number_do_not_collide(self):
        self._doc(self.doc_type, company_id=False)
        self._doc(self.doc_type, company_id=False)
        self.env.flush_all()


class TestExpirationTimezone(DocumentTypeCase):
    EVENING = "2026-08-28 01:00:00"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.partner_id.tz = "America/Mexico_City"
        cls.doc_type = cls._type("TZ")
        cls.env.ref("base.user_admin").tz = False

    def test_the_server_and_the_tenant_disagree_at_that_hour(self):
        with freeze_time(self.EVENING):
            self.assertEqual(date.today(), date(2026, 8, 28))
            self.assertEqual(
                self.env["document.document"]._get_expiration_today(self.company),
                date(2026, 8, 27),
            )

    def test_every_reading_uses_the_companys_day(self):
        with freeze_time(self.EVENING):
            doc = self._doc(self.doc_type, date_expiration=date(2026, 8, 27))

            self.assertEqual(self._stored_state(doc), "expiring_soon")
            self.assertEqual(doc.days_left, 0)

    def test_a_company_without_a_zone_reads_the_users_day(self):
        self.company.partner_id.tz = False
        with freeze_time(self.EVENING):
            self.assertEqual(
                self.env["document.document"]._get_expiration_today(self.company),
                date(2026, 8, 28),
            )

    def test_each_company_reads_its_own_day(self):
        other = self.env["res.company"].create(
            {
                "name": "Tokyo Co",
                "partner_id": self.env["res.partner"]
                .create({"name": "Tokyo Co", "tz": "Asia/Tokyo"})
                .id,
            }
        )
        global_type = self.env["document.type"].create(
            {"name": "Global TZ", "code": "TZ_GLOBAL", "company_id": False}
        )
        with freeze_time("2026-08-28 20:00:00"):
            local = self._doc(self.doc_type, date_expiration=date(2026, 8, 28))
            remote = self._doc(
                global_type, date_expiration=date(2026, 8, 28), company_id=other.id
            )

            self.assertEqual(
                local.expiration_state,
                "expiring_soon",
                "Mexico City is still on the 28th",
            )
            self.assertEqual(
                remote.expiration_state, "expired", "Tokyo is already on the 29th"
            )


class TestRefreshCron(DocumentTypeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type = cls._type("REFRESH")

    def _refresh(self):
        self.env.invalidate_all()
        self.env["document.document"]._cron_refresh_expiration_state()
        self.env.flush_all()

    def test_cron_moves_a_valid_document_to_expiring_soon(self):
        with freeze_time("2026-08-27"):
            doc = self._doc(self.doc_type, date_expiration=date(2026, 10, 11))
            self.assertEqual(self._stored_state(doc), "valid")

        with freeze_time("2026-09-27"):
            self.assertEqual(self._stored_state(doc), "valid", "stale on its own")
            self._refresh()
            self.assertEqual(self._stored_state(doc), "expiring_soon")

    def test_cron_moves_a_document_to_expired(self):
        with freeze_time("2026-08-27"):
            doc = self._doc(self.doc_type, date_expiration=date(2026, 9, 5))
            self.assertEqual(self._stored_state(doc), "expiring_soon")

        with freeze_time("2026-09-20"):
            self._refresh()
            self.assertEqual(self._stored_state(doc), "expired")

    def test_cron_leaves_a_far_future_document_alone(self):
        with freeze_time("2026-08-27"):
            doc = self._doc(self.doc_type, date_expiration=date(2027, 8, 27))
            self._refresh()
            self.assertEqual(self._stored_state(doc), "valid")

    def test_cron_ignores_a_non_expiring_type(self):
        quiet = self._type("REFRESH_QUIET", has_expiration=False)
        with freeze_time("2026-08-27"):
            doc = self._doc(quiet, date_expiration=date(2026, 9, 5))

        with freeze_time("2026-09-20"):
            self._refresh()
            self.assertIsNone(self._stored_state(doc))

    def test_cron_repairs_a_stale_stored_flag(self):
        doc = self._doc(self.doc_type, -5)
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE document_document SET expiration_state = 'valid' WHERE id = %s",
            (doc.id,),
        )

        self._refresh()

        self.assertEqual(self._stored_state(doc), "expired")


class TestCounters(DocumentTypeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.doc_type = cls._type("STAT")
        for name, days in (
            ("Valid A", 200),
            ("Valid B", 300),
            ("Expiring", 10),
            ("Expired", -10),
        ):
            cls._doc(cls.doc_type, days, name=name)

    def test_the_counters_split_the_documents_by_state(self):
        self.assertEqual(self.doc_type.document_count, 4)
        self.assertEqual(self.doc_type.expired_document_count, 1)
        self.assertEqual(self.doc_type.expiring_soon_count, 1)

    def test_each_button_opens_exactly_what_it_counted(self):
        cases = (
            (None, self.doc_type.document_count),
            ("expired", self.doc_type.expired_document_count),
            ("expiring_soon", self.doc_type.expiring_soon_count),
        )
        for expiration_filter, counted in cases:
            with self.subTest(expiration_filter=expiration_filter):
                doc_type = self.doc_type
                if expiration_filter:
                    doc_type = doc_type.with_context(
                        expiration_filter=expiration_filter
                    )
                action = doc_type.action_view_documents()
                opened = self.env["document.document"].search(action["domain"])
                self.assertEqual(len(opened), counted)
                self.assertEqual(action["res_model"], "document.document")

    def test_counters_follow_documents_without_manual_invalidation(self):
        other = self._type("STAT_OTHER")
        self.assertEqual(other.document_count, 0)

        doc = self._doc(other, 60)
        self.assertEqual(other.document_count, 1)
        self.assertEqual(other.expiring_soon_count, 0)

        doc.date_expiration = date.today() + timedelta(days=10)
        self.assertEqual(other.expiring_soon_count, 1)

        doc.document_type_id = False
        self.assertEqual(other.document_count, 0)


class TestOnchangeDocumentType(DocumentTypeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.target_folder = cls.env["document.document"].create(
            {"name": "Target Folder", "type": "folder"}
        )
        cls.tag = cls.env["document.tag"].create({"name": "Onchange Tag"})
        cls.doc_type = cls._type(
            "ONCHANGE",
            default_validity_days=180,
            folder_id=cls.target_folder.id,
            tag_ids=[(4, cls.tag.id)],
        )

    def _new(self, **vals):
        doc = self.env["document.document"].new(
            {"name": "Onchange Test", "folder_id": self.folder.id, **vals}
        )
        doc.document_type_id = self.doc_type
        doc._onchange_document_type_id()
        return doc

    def test_onchange_sets_folder_and_adds_tags(self):
        other_tag = self.env["document.tag"].create({"name": "Kept Tag"})
        doc = self._new(tag_ids=[(4, other_tag.id)])

        self.assertEqual(doc.folder_id, self.target_folder)
        self.assertEqual(set(doc.tag_ids.ids), {self.tag.id, other_tag.id})

    def test_onchange_fills_dates_from_the_type(self):
        doc = self._new()

        self.assertEqual(doc.date_issued, date.today())
        self.assertEqual(doc.date_expiration, date.today() + timedelta(days=180))

    def test_onchange_keeps_an_issued_date_and_counts_validity_from_it(self):
        issued = date.today() - timedelta(days=30)
        doc = self._new(date_issued=issued)

        self.assertEqual(doc.date_issued, issued)
        self.assertEqual(doc.date_expiration, issued + timedelta(days=180))

    def test_onchange_never_overwrites_an_expiration(self):
        existing = date.today() + timedelta(days=30)
        doc = self._new(date_issued=date.today(), date_expiration=existing)

        self.assertEqual(doc.date_expiration, existing)


class TestRenewalChain(DocumentTypeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.renewable_type = cls._type("RENEW", default_validity_days=365)
        cls.non_renewable_type = cls._type("NORENEW", is_renewable=False)

    def test_renewal_count_walks_the_chain_and_follows_inserts(self):
        doc_b = self._doc(self.renewable_type, name="B")
        doc_c = self._doc(self.renewable_type, name="C", renewal_document_id=doc_b.id)
        self.assertEqual(doc_c.renewal_count, 1)

        doc_a = self._doc(self.renewable_type, name="A")
        doc_b.renewal_document_id = doc_a
        self.assertEqual(doc_c.renewal_count, 2)
        self.assertEqual(doc_b.renewed_by_document_id, doc_c)
        self.assertEqual(doc_a.renewed_by_document_id, doc_b)

    def test_cycles_are_rejected(self):
        doc_a = self._doc(self.renewable_type, name="A")
        doc_b = self._doc(self.renewable_type, name="B", renewal_document_id=doc_a.id)
        doc_c = self._doc(self.renewable_type, name="C", renewal_document_id=doc_b.id)

        for target in (doc_a, doc_b, doc_c):
            with self.subTest(target=target.name), self.assertRaises(ValidationError):
                doc_a.renewal_document_id = target

    def test_two_documents_cannot_renew_the_same_one(self):
        doc_a = self._doc(self.renewable_type, name="A")
        self._doc(self.renewable_type, name="B", renewal_document_id=doc_a.id)
        self.env.flush_all()

        with self.assertRaises(IntegrityError), self.env.cr.savepoint():
            self._doc(self.renewable_type, name="C", renewal_document_id=doc_a.id)
            self.env.flush_all()

    def test_renew_starts_a_fresh_linked_document_without_the_old_file(self):
        original = self._doc(
            self.renewable_type,
            -10,
            name="Original License",
            legal_number="LN-ORIGINAL",
            datas=base64.b64encode(b"OLD FILE"),
            mimetype="text/plain",
        )

        action = original.action_renew_document()
        new_doc = self.env["document.document"].browse(action["res_id"])

        self.assertEqual(new_doc.renewal_document_id, original)
        self.assertEqual(original.renewed_by_document_id, new_doc)
        self.assertEqual(new_doc.renewal_count, 1)
        self.assertIn("(Renewal)", new_doc.name)
        self.assertFalse(
            new_doc.attachment_id,
            "a renewal awaits its own upload; the expired file must not travel",
        )
        self.assertEqual(new_doc.date_issued, date.today())
        self.assertEqual(new_doc.date_expiration, date.today() + timedelta(days=365))
        self.assertEqual(new_doc.expiration_state, "valid")
        self.assertFalse(new_doc.legal_number)
        self.assertEqual(original.legal_number, "LN-ORIGINAL")
        self.assertEqual(original.attachment_id.raw, b"OLD FILE")

    def test_a_document_cannot_be_renewed_twice(self):
        original = self._doc(self.renewable_type, name="Twice")
        first = self.env["document.document"].browse(
            original.action_renew_document()["res_id"]
        )

        with self.assertRaises(UserError):
            original.action_renew_document()

        self.assertEqual(original.renewed_by_document_id, first)

    def test_renew_non_renewable_raises(self):
        doc = self._doc(self.non_renewable_type)

        with self.assertRaises(UserError):
            doc.action_renew_document()


class TestRenewalState(DocumentTypeCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.renewable_type = cls._type("RSTATE", default_validity_days=365)

    def _stored_renewal_state(self, doc):
        self.env.flush_all()
        self.env.cr.execute(
            "SELECT renewal_state FROM document_document WHERE id = %s", (doc.id,)
        )
        return self.env.cr.fetchone()[0]

    def test_states(self):
        cases = (
            (self.renewable_type, 60, False),
            (self.renewable_type, 10, "due"),
            (self.renewable_type, -10, "due"),
            (self.renewable_type, None, "due"),
            (self._type("RSTATE_NO", is_renewable=False), -10, False),
            (self._type("RSTATE_STATIC", has_expiration=False), None, False),
        )
        for doc_type, days, expected in cases:
            with self.subTest(type=doc_type.code, days=days):
                doc = self._doc(doc_type, days)
                self.assertEqual(doc.renewal_state, expected)

    def test_renewing_moves_due_to_renewed_and_the_renewal_starts_clean(self):
        original = self._doc(self.renewable_type, -10)
        self.assertEqual(original.renewal_state, "due")

        new_doc = self.env["document.document"].browse(
            original.action_renew_document()["res_id"]
        )

        self.assertEqual(self._stored_renewal_state(original), "renewed")
        self.assertFalse(new_doc.renewal_state)

    def test_the_refresh_cron_moves_a_document_into_due(self):
        with freeze_time("2026-08-27"):
            doc = self._doc(self.renewable_type, date_expiration=date(2026, 10, 11))
            self.assertIsNone(self._stored_renewal_state(doc))

        with freeze_time("2026-09-27"):
            self.env.invalidate_all()
            self.env["document.document"]._cron_refresh_expiration_state()
            self.assertEqual(self._stored_renewal_state(doc), "due")


@tagged("post_install", "-at_install")
class TestExpirationRefreshCronIsUserIndependent(DocumentTypeCase):
    """The refresh sweep must not be scoped to whoever runs the cron.

    `expiration_state` is stored and its value is a function of today's date,
    so a daily sweep is the only thing keeping it true. That sweep used to run
    a plain `self.search()`, gated by the `user_permission != 'none'` record
    rule. The shipped `ir.cron` runs as `__system__` -- SUPERUSER_ID, which
    bypasses every rule -- so the dependency was invisible. Point it at an
    ordinary account, which `ir_cron.user_id` exists to allow, and the sweep
    silently refreshed nothing and still returned True.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_company = cls.env["res.company"].create({"name": "Cron Co"})
        cls.cron_user = cls.env["res.users"].create(
            {
                "name": "Cron Bot",
                "login": "document_cron_bot",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            cls.env.ref("base.group_user").id,
                            cls.env.ref("document.group_documents_manager").id,
                        ],
                    )
                ],
                "company_ids": [(6, 0, [cls.env.company.id, cls.other_company.id])],
                "company_id": cls.env.company.id,
            }
        )

    def _stale_documents(self):
        """Two documents whose stored state disagrees with their date.

        Written behind the ORM's back on purpose: going through `write` would
        recompute the field and leave nothing for the cron to find.
        """
        document_type = self.env["document.type"].create(
            {
                "name": "Cron Type",
                "code": "crontype",
                "has_expiration": True,
                # company-less: the documents below deliberately straddle two
                # companies, and `_check_document_type_company` refuses a typed
                # document whose company differs from its type's.
                "company_id": False,
            }
        )
        today = date.today()
        documents = self.env["document.document"].create(
            [
                {
                    "name": f"expiring-{index}.pdf",
                    "type": "binary",
                    "document_type_id": document_type.id,
                    "company_id": company.id,
                    "date_expiration": today + timedelta(days=90),
                }
                for index, company in enumerate((self.env.company, self.other_company))
            ]
        )
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE document_document SET date_expiration = %s WHERE id = ANY(%s)",
            (today + timedelta(days=10), documents.ids),
        )
        self.env.invalidate_all()
        self.assertEqual(
            documents.mapped("expiration_state"),
            ["valid", "valid"],
            "the fixture must start stale, or the cron has nothing to do",
        )
        return documents

    def test_an_ordinary_cron_user_refreshes_every_company(self):
        documents = self._stale_documents()

        self.env["document.document"].with_user(self.cron_user).with_context(
            {}
        )._cron_refresh_expiration_state()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            documents.mapped("expiration_state"),
            ["expiring_soon", "expiring_soon"],
            "the sweep is scoped to the cron user's readable set again",
        )

    def test_the_shipped_superuser_cron_still_refreshes(self):
        """Negative control: the arm that always worked must keep working."""
        documents = self._stale_documents()

        self.env["document.document"].with_user(
            self.env.ref("base.user_root")
        ).with_context({})._cron_refresh_expiration_state()
        self.env.flush_all()
        self.env.invalidate_all()

        self.assertEqual(
            documents.mapped("expiration_state"),
            ["expiring_soon", "expiring_soon"],
        )
