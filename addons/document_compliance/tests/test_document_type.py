from odoo.exceptions import ValidationError

from .common import ComplianceCase
from odoo.addons.document_compliance.models.document_type import (
    MAX_NOTIFICATION_DAYS,
)


class TestDocumentTypeDefaults(ComplianceCase):
    def test_defaults(self):
        doc_type = self._type("WP")

        self.assertFalse(doc_type.is_mandatory)
        self.assertFalse(doc_type.requires_original)
        self.assertEqual(doc_type.notification_days, "30,7,1")
        self.assertEqual(doc_type.applies_to, "all")

    def test_applies_to_lists_only_installed_entity_models(self):
        selection = dict(self.env["document.type"]._selection_applies_to())

        self.assertIn("all", selection)
        self.assertIn("res.partner", selection)
        self.assertNotIn("fleet.vehicle", selection)


class TestNotificationDays(ComplianceCase):
    def test_valid_list_round_trips(self):
        doc_type = self._type("LIC", notification_days="60,30,14,7,1")

        self.assertEqual(doc_type._get_notification_days(), [60, 30, 14, 7, 1])

    def test_empty_means_no_notifications(self):
        doc_type = self._type("EMPTY", notification_days=False)

        self.assertEqual(doc_type._get_notification_days(), [])

    def test_rejects_garbage_negatives_and_duplicates(self):
        for value in ("abc,30,7", "-5,30,7", "30,30,7", "0"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                self._type(f"BAD_{abs(hash(value)) % 1000}", notification_days=value)

    def test_rejects_a_value_past_the_ceiling(self):
        with self.assertRaises(ValidationError):
            self._type("TOOWIDE", notification_days=str(MAX_NOTIFICATION_DAYS + 1))

    def test_accepts_the_ceiling_itself(self):
        doc_type = self._type("ATCAP", notification_days=str(MAX_NOTIFICATION_DAYS))

        self.assertEqual(doc_type._get_notification_days(), [MAX_NOTIFICATION_DAYS])

    def test_widest_threshold_spans_every_expiring_type(self):
        self.env["document.type"].search([]).write({"has_expiration": False})
        self._type("W1", notification_days="30,7")
        self._type("W2", notification_days="90")
        self._type("W3", notification_days="180", has_expiration=False)

        self.assertEqual(
            self.env["document.type"]._get_widest_notification_days(),
            90,
            "a type that never expires does not widen the cron window",
        )
