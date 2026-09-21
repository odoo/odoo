from datetime import datetime
from unittest.mock import Mock, patch

from freezegun import freeze_time

from odoo import Command
from odoo.tests import new_test_user, tagged

from odoo.addons.gateway_ml.tests.test_model_selection import _SelectionCase
from odoo.addons.gateway_ml.tools import MlRequest, MlRouter
from odoo.addons.integration.tools.exceptions import CommError

OPEN = "test.policy.open"
SECRET = "test.policy.secret"
PARENT = "speech.transcription"
CHILD = "speech.transcription.call"


@tagged("post_install", "-at_install")
class TestMlPolicy(_SelectionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Purpose = cls.env["gateway.ml.purpose"]
        cls.Policy = cls.env["gateway.ml.policy"]
        cls.company_id = cls.env.company.id
        cls.alpha = cls._provider("pol_alpha")
        cls.beta = cls._provider("pol_beta")
        cls.unkeyed = cls._provider("pol_unkeyed", keyed=False)
        cls.alpha_model = cls._model(cls.alpha, "pol-alpha-m", accuracy_rating="2")
        cls.alpha_sibling = cls._model(cls.alpha, "pol-alpha-sibling")
        cls.beta_model = cls._model(cls.beta, "pol-beta-m", accuracy_rating="5")
        cls._model(cls.unkeyed, "pol-unkeyed-m")
        cls.vendors = cls.alpha | cls.beta | cls.unkeyed
        cls.Purpose.create({"key": SECRET, "sensitive": True})
        cls.Purpose._get_for(PARENT).sensitive = True

    def _allow(self, key, *providers):
        return self.Policy.create(
            {
                "company_id": self.company_id,
                "purpose_id": self.Purpose._get_for(key).id,
                "provider_ids": [Command.set([p.id for p in providers])],
            }
        )

    def _usable(self, key, providers=None):
        return self.router._get_usable_providers(
            self.vendors if providers is None else providers, self.company_id, key
        )

    def _run(self, key, model=None):
        client = Mock(complete=Mock(return_value="ok"))
        with patch.object(MlRouter, "_get_client", return_value=client):
            result = self.router.run(
                "chat",
                MlRequest(purpose=key, prompt="q"),
                model=model,
                company_id=self.company_id,
            )
        return result, client

    def test_a_purpose_nobody_declared_sensitive_reaches_every_keyed_vendor(self):
        self.assertEqual(self._usable(OPEN), self.alpha | self.beta)
        self.assertEqual(self._select("chat", purpose=OPEN), self.beta_model)

    def test_a_sensitive_purpose_with_no_policy_reaches_no_vendor(self):
        self.assertFalse(self._usable(SECRET))
        self.assertFalse(self._select("chat", purpose=SECRET))
        with self.assertRaises(CommError):
            self._run(SECRET)

    def test_a_policy_opens_a_sensitive_purpose_to_the_vendors_it_names(self):
        self._allow(SECRET, self.alpha, self.unkeyed)
        self.assertEqual(self._usable(SECRET), self.alpha)
        self.assertEqual(self._select("chat", purpose=SECRET).provider_id, self.alpha)

    def test_a_policy_narrows_a_purpose_that_is_not_sensitive(self):
        self._allow(OPEN, self.alpha)
        self.assertEqual(self._usable(OPEN), self.alpha)

    def test_a_policy_is_the_companys_own(self):
        self._allow(SECRET, self.alpha)
        other = self.env["res.company"].create({"name": "Other policy company"})
        self.assertFalse(
            self.router._get_usable_providers(self.vendors, other.id, SECRET)
        )

    def test_a_policy_on_the_parent_key_governs_a_child_key(self):
        self._allow(PARENT, self.alpha)
        self.assertEqual(self._usable(CHILD), self.alpha)

    def test_a_child_of_a_sensitive_purpose_is_sensitive(self):
        self.assertTrue(self.Purpose._is_sensitive(CHILD))
        self.assertFalse(self._usable(CHILD))

    def test_the_most_specific_policy_wins_over_its_parent(self):
        self._allow(PARENT, self.alpha)
        self._allow(CHILD, self.beta)
        self.assertEqual(self._usable(CHILD), self.beta)
        self.assertEqual(self._usable(f"{CHILD}.inbound"), self.beta)
        self.assertEqual(self._usable(PARENT), self.alpha)
        self.assertEqual(self._usable("speech.transcription.meeting"), self.alpha)

    def test_a_child_policy_naming_no_vendor_closes_what_its_parent_opened(self):
        self._allow(PARENT, self.alpha, self.beta)
        self._allow(CHILD)
        self.assertFalse(self._usable(CHILD))

    def test_the_lineage_runs_from_the_key_to_its_root(self):
        self.assertEqual(
            self.Purpose._lineage(CHILD),
            [CHILD, PARENT, "speech"],
        )

    def test_a_fallback_hop_whose_vendor_the_policy_does_not_name_is_skipped(self):
        self._allow(SECRET, self.alpha)
        self.alpha_model.fallback_model_ids = [
            Command.set([self.beta_model.id, self.alpha_sibling.id])
        ]
        self.assertEqual(
            self.router._get_runnable_chain(
                self.alpha_model, None, self.company_id, SECRET
            ),
            [self.alpha_model, self.alpha_sibling],
        )
        self.assertEqual(
            self.router._get_runnable_chain(
                self.alpha_model, None, self.company_id, OPEN
            ),
            [self.alpha_model, self.beta_model, self.alpha_sibling],
        )

    def test_a_model_passed_to_run_whose_vendor_is_forbidden_is_not_used(self):
        self._allow(SECRET, self.alpha)

        result, client = self._run(SECRET, model=self.beta_model)

        self.assertEqual(result.model.provider_id, self.alpha)
        self.assertEqual(client.complete.call_args.kwargs["model"], result.model.code)

    def test_a_forbidden_model_with_no_allowed_replacement_is_not_called(self):
        self._allow(SECRET)
        client = Mock(complete=Mock(return_value="ok"))
        with patch.object(MlRouter, "_get_client", return_value=client):
            with self.assertRaises(CommError):
                self.router.run(
                    "chat",
                    MlRequest(purpose=SECRET, prompt="q"),
                    model=self.beta_model,
                    company_id=self.company_id,
                )
        client.complete.assert_not_called()

    def test_a_model_passed_to_run_that_the_policy_allows_is_used(self):
        self._allow(SECRET, self.alpha, self.beta)

        result, _client = self._run(SECRET, model=self.alpha_model)

        self.assertEqual(result.model, self.alpha_model)

    def test_the_approval_is_stamped_on_create(self):
        with freeze_time("2026-03-01 10:00:00"):
            policy = self._allow(SECRET, self.alpha)
        self.assertEqual(policy.approved_by_id, self.env.user)
        self.assertEqual(policy.approved_at, datetime(2026, 3, 1, 10, 0))

    def test_changing_the_vendors_is_a_new_approval(self):
        with freeze_time("2026-03-01 10:00:00"):
            policy = self._allow(SECRET, self.alpha)
        approver = new_test_user(self.env, login="policy_approver")

        with freeze_time("2026-03-02 09:00:00"):
            policy.with_user(approver).sudo().write(
                {"provider_ids": [Command.link(self.beta.id)]}
            )

        self.assertEqual(policy.approved_by_id, approver)
        self.assertEqual(policy.approved_at, datetime(2026, 3, 2, 9, 0))

    def test_editing_the_note_keeps_the_approval(self):
        with freeze_time("2026-03-01 10:00:00"):
            policy = self._allow(SECRET, self.alpha)
        editor = new_test_user(self.env, login="policy_editor")

        with freeze_time("2026-03-02 09:00:00"):
            policy.with_user(editor).sudo().write({"note": "reviewed"})

        self.assertEqual(policy.approved_by_id, self.env.user)
        self.assertEqual(policy.approved_at, datetime(2026, 3, 1, 10, 0))

    def test_get_for_records_an_unknown_purpose_once(self):
        key = "test.policy.unheard.of"
        self.assertFalse(self.Purpose.search([("key", "=", key)]))

        first = self.Purpose._get_for(key)
        second = self.Purpose._get_for(key)

        self.assertEqual(first, second)
        self.assertEqual(self.Purpose.search_count([("key", "=", key)]), 1)
        self.assertFalse(first.sensitive)

    def test_run_records_the_purpose_it_is_asked_for(self):
        key = "test.policy.recorded"

        self._run(key)

        self.assertEqual(self.Purpose.search_count([("key", "=", key)]), 1)

    def test_run_without_a_purpose_is_refused(self):
        client = Mock(complete=Mock(return_value="ok"))
        with patch.object(MlRouter, "_get_client", return_value=client):
            with self.assertRaises(ValueError):
                self.router.run(
                    "chat", MlRequest(prompt="q"), company_id=self.company_id
                )
        client.complete.assert_not_called()
