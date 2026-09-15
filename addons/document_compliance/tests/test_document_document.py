from datetime import date

from freezegun import freeze_time

from .common import ComplianceCase


class TestComplianceState(ComplianceCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expiring_type = cls._type("EXP")
        cls.non_expiring_type = cls._type("NOEXP", has_expiration=False)

    def test_states(self):
        cases = (
            (self.expiring_type, 60, "valid", "compliant"),
            (self.expiring_type, 0, "expiring_soon", "compliant"),
            (self.expiring_type, -10, "expired", "non_compliant"),
            (self.expiring_type, None, "missing", "non_compliant"),
            (self.non_expiring_type, None, False, "compliant"),
            (self.non_expiring_type, -10, False, "compliant"),
            (None, 60, False, "na"),
            (None, -30, False, "na"),
        )
        for doc_type, days, expiration, compliance in cases:
            with self.subTest(type=doc_type and doc_type.code, days=days):
                doc = self._doc(doc_type, days)
                self.assertEqual(doc.expiration_state, expiration)
                self.assertEqual(doc.compliance_state, compliance)

    def test_compliance_follows_the_type_not_the_date(self):
        doc = self._doc(self.expiring_type, -10)
        self.assertEqual(
            (doc.expiration_state, doc.compliance_state), ("expired", "non_compliant")
        )

        doc.document_type_id = self.non_expiring_type
        self.assertEqual(
            (doc.expiration_state, doc.compliance_state),
            (False, "compliant"),
            "the type says the date does not matter",
        )

        doc.document_type_id = False
        self.assertEqual((doc.expiration_state, doc.compliance_state), (False, "na"))

    def test_expiring_today_is_still_compliant(self):
        doc = self._doc(self.expiring_type, 0)

        self.assertEqual(doc.compliance_state, "compliant")

    def test_the_refresh_cron_moves_the_verdict_with_the_state(self):
        with freeze_time("2026-08-27"):
            doc = self._doc(self.expiring_type, date_expiration=date(2026, 9, 5))
            self.assertEqual(self._stored(doc), ("expiring_soon", "compliant"))

        with freeze_time("2026-09-20"):
            self.env.invalidate_all()
            self.env["document.document"]._cron_refresh_expiration_state()
            self.assertEqual(self._stored(doc), ("expired", "non_compliant"))


class TestRenewal(ComplianceCase):
    def test_renew_does_not_inherit_the_verification_or_notification_record(self):
        original = self._doc(
            self._type("RENEW", default_validity_days=365),
            -10,
            date_verification=date(2020, 1, 1),
            verified_by_user_id=self.admin.id,
            verification_notes="checked in 2020",
            notification_last_days=1,
            notification_sent_expired=True,
        )

        new_doc = self.env["document.document"].browse(
            original.action_renew_document()["res_id"]
        )

        self.assertEqual(new_doc.compliance_state, "compliant")
        for field_name in (
            "date_verification",
            "verified_by_user_id",
            "verification_notes",
            "notification_last_days",
            "notification_sent_expired",
        ):
            self.assertFalse(new_doc[field_name], field_name)


class TestVerification(ComplianceCase):
    def test_action_verify_document(self):
        doc = self._doc()

        result = doc.action_record_verification()

        self.assertEqual(doc.date_verification, date.today())
        self.assertEqual(doc.verified_by_user_id, self.env.user)
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
