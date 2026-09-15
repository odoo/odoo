from datetime import date, timedelta

from freezegun import freeze_time

from .common import ComplianceCase


class TestNotificationThresholds(ComplianceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.recipient = cls.admin.partner_id

    def _notified_type(self, code, notification_days="30,7,1"):
        return self._type(
            code,
            notification_days=notification_days,
            notification_partner_ids=[(6, 0, self.recipient.ids)],
        )

    def _cron(self):
        self.env["document.document"].cron_document_notifications()

    def test_thresholds_are_ranges_read_from_the_real_days_left(self):
        doc_type = self._notified_type("THR")
        cases = (
            (31, 0, []),
            (30, 30, ["Document expiring in 30 days"]),
            (29, 30, ["Document expiring in 29 days"]),
            (3, 7, ["Document expiring in 3 days"]),
        )
        for days, expected_last, summaries in cases:
            with self.subTest(days=days):
                doc = self._doc(doc_type, days)
                self._cron()
                self.assertEqual(doc.notification_last_days, expected_last)
                self.assertEqual(self._activities(doc).mapped("summary"), summaries)

    def test_a_configured_day_outside_30_7_1_notifies(self):
        doc = self._doc(self._notified_type("THR_SIXTY", "60"), 60)

        self._cron()

        self.assertEqual(
            self._activities(doc).mapped("summary"), ["Document expiring in 60 days"]
        )
        self.assertEqual(doc.notification_last_days, 60)

    def test_each_threshold_fires_once_as_expiration_approaches(self):
        doc = self._doc(self._notified_type("THR_WALK", "90,30,7"), 90)

        self._cron()
        self.assertEqual(doc.notification_last_days, 90)
        self._cron()
        self.assertEqual(len(self._activities(doc)), 1)

        doc.date_expiration = date.today() + timedelta(days=20)
        self._cron()
        self.assertEqual(doc.notification_last_days, 30)
        self.assertEqual(len(self._activities(doc)), 2)

    def test_a_type_without_a_30_day_threshold_skips_it(self):
        doc = self._doc(self._notified_type("SHORT", "7,1"), 25)

        self._cron()

        self.assertEqual(doc.notification_last_days, 0)
        self.assertFalse(self._activities(doc))

    def test_expired_activity_fires_the_day_after_expiration(self):
        doc_type = self._notified_type("EXPD")
        today_doc = self._doc(doc_type, 0)
        yesterday_doc = self._doc(doc_type, -1)

        self._cron()

        self.assertFalse(today_doc.notification_sent_expired)
        self.assertEqual(today_doc.expiration_state, "expiring_soon")
        self.assertEqual(
            self._activities(today_doc).mapped("summary"),
            ["Document expires today"],
            "on its last valid day the document is still expiring, not expired",
        )
        self.assertTrue(yesterday_doc.notification_sent_expired)
        self.assertEqual(
            self._activities(yesterday_doc).mapped("summary"), ["Document expired"]
        )

    def test_a_document_without_a_recipient_stays_pending(self):
        doc = self._doc(self._type("NOREC", notification_days="30,7,1"), 10)

        with self.assertLogs(
            "odoo.addons.document_compliance.models.document_document", level="WARNING"
        ):
            self._cron()

        self.assertFalse(self._activities(doc))
        self.assertEqual(doc.notification_last_days, 0)

        doc.owner_id = self.admin
        self._cron()

        self.assertEqual(
            self._activities(doc).mapped("summary"), ["Document expiring in 10 days"]
        )
        self.assertEqual(doc.notification_last_days, 30)

    def test_one_run_notifies_every_company_and_the_shared_documents(self):
        doc_type = self._notified_type("WINDOWS")
        doc_type.company_id = False
        other = self.env["res.company"].create({"name": "Second Compliance Co"})
        docs = (
            self._doc(doc_type, 5, name="Main"),
            self._doc(doc_type, 5, name="Other", company_id=other.id),
            self._doc(doc_type, -1, name="Shared", company_id=False),
        )

        self._cron()

        self.assertEqual(
            [self._activities(doc).mapped("summary") for doc in docs],
            [
                ["Document expiring in 5 days"],
                ["Document expiring in 5 days"],
                ["Document expired"],
            ],
        )

    def test_an_activity_already_on_the_document_is_not_repeated(self):
        doc = self._doc(self._notified_type("AGAIN"), 5)
        doc._send_expiration_notification(5)

        self.assertTrue(doc._send_expiration_notification(5))

        self.assertEqual(len(self._activities(doc)), 1)

    def test_a_document_with_no_type_gets_no_expired_activity(self):
        doc = self._doc(None, -2, owner_id=self.admin.id)

        self._cron()

        self.assertFalse(self._activities(doc))
        self.assertFalse(doc.notification_sent_expired)

    def test_a_non_expiring_type_gets_no_activity_for_a_stray_date(self):
        quiet = self._notified_type("QUIET")
        quiet.has_expiration = False
        doc = self._doc(quiet, -2)

        self._cron()

        self.assertFalse(self._activities(doc))
        self.assertFalse(doc.notification_sent_expired)

    def test_the_note_carries_the_renewal_instructions(self):
        doc_type = self._notified_type("NOTE")
        doc_type.instructions = "<p>Go to the office</p>"
        doc = self._doc(doc_type, 5, name="A <b>named</b> doc")

        self._cron()

        note = self._activities(doc).note
        self.assertIn("A &lt;b&gt;named&lt;/b&gt; doc", note)
        self.assertIn("<p>Go to the office</p>", note)


class TestNotificationTimezone(ComplianceCase):
    EVENING = "2026-08-28 01:00:00"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.partner_id.tz = "America/Mexico_City"
        cls.doc_type = cls._type(
            "TZ", notification_partner_ids=[(6, 0, cls.admin.partner_id.ids)]
        )
        cls.admin.tz = False

    def test_the_notifier_reads_the_companys_day(self):
        with freeze_time(self.EVENING):
            doc = self._doc(self.doc_type, date_expiration=date(2026, 8, 27))

            self.env["document.document"].cron_document_notifications()

            self.assertEqual(
                self._activities(doc).mapped("summary"), ["Document expires today"]
            )
            self.assertFalse(doc.notification_sent_expired)
