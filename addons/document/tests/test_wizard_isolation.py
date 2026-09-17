"""One user's open wizard is not another user's record.

Every wizard this module ships is a `TransientModel` whose ACL grants read and
write to `base.group_user` as a whole, so without an owner record rule any
internal user reaches any other's live wizard by id. `document.operation`
carried such a rule from the start (`document_operation_rwu`); its four
siblings did not, and `document.sharing` is the one that costs something:
`invite_partner_ids` is who you are about to share with, and `invite_role` is
what they will get -- writable by anyone, right up until you press the button.

The roster is DERIVED from the registry rather than listed, because a listed
roster only covers the wizards somebody remembered to list. `_wizard_models`
finds them; `_builders` says how a real user opens each; and
`test_the_roster_and_the_fixtures_agree` fails when a new wizard appears with
no fixture, so adding a wizard is what puts it under test.

The isolation itself is asserted BEHAVIOURALLY -- a stranger really tries to
read and to write -- not by pattern-matching `domain_force` for "create_uid",
which `[('create_uid','!=',user.id)]` would also satisfy.
"""

import contextlib

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests.common import tagged
from odoo.tools.safe_eval import safe_eval

from .test_document_common import TransactionCaseDocuments


@tagged("post_install", "-at_install")
class TestWizardIsolation(TransactionCaseDocuments):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.owner_env = cls.env(user=cls.doc_user)
        cls.stranger_env = cls.env(user=cls.doc_user_2)
        cls.counterparty = cls.env["res.partner"].create(
            {"name": "Confidential Counterparty", "email": "cc@example.com"}
        )
        # Owned by the wizard owner, so `action_open` is reachable for them:
        # the subject of the wizard is not what is under test here.
        cls.subject = cls.owner_env["document.document"].create(
            {"name": "subject.txt", "type": "binary", "raw": b"s"}
        )

    def _builders(self):
        """One builder per wizard: how a real user actually opens it.

        `document.sharing` is built through `action_open` rather than a raw
        `create`, because four of its selections are `required=True` and it is
        `action_open` that fills them -- a hand-written vals dict here would be
        testing a row the application never produces.
        """

        def sharing(env):
            return env["document.sharing"].browse(
                env["document.sharing"].action_open(self.subject.ids)["res_id"]
            )

        return {
            "document.sharing": sharing,
            "document.sharing.access": lambda env: (
                sharing(env).share_access_ids[:1]
                or env["document.sharing.access"].create(
                    {"role": "view", "documents_sharing_id": sharing(env).id}
                )
            ),
            "document.operation": lambda env: env["document.operation"].create(
                {"operation": "move", "destination": "MY"}
            ),
            "document.request_wizard": lambda env: env[
                "document.request_wizard"
            ].create(
                {
                    "name": "please upload",
                    "requestee_id": env.user.partner_id.id,
                }
            ),
            "document.link_to_record_wizard": lambda env: env[
                "document.link_to_record_wizard"
            ].create({"document_ids": [Command.set(self.subject.ids)]}),
        }

    def _wizard_models(self):
        """Every transient model this module defines.

        No ACL filter. A first version of this filtered on ACLs granted to
        `base.group_user` / `base.group_portal`, and a mutation check -- with
        the new rules switched off -- reported only two of the four wizards as
        reachable: `document.request_wizard` and `document.link_to_record_wizard`
        are opened to `document.group_documents_user` instead, so the filter
        skipped them and the sweep passed over the exact models it existed to
        cover. A transient record is per-user state whoever the ACL names, so
        the roster is every one of them.
        """
        return {
            name
            for name in self.env.registry
            if name.startswith("document.")
            and (model := self.env.get(name)) is not None
            and model._transient
        }

    def _owner_rule_models(self):
        """Models carrying an active rule that restricts rows to their creator.

        The domain is evaluated the way `ir.rule` evaluates it and its leaves
        are inspected. Two weaker versions were tried and are worth not
        repeating: `"create_uid" in domain_force` also accepts
        `[('create_uid', '!=', user.id)]`, the opposite rule; and
        `literal_eval` cannot evaluate `user.id`, so it raised on exactly the
        rules being looked for and reported every wizard as unprotected.
        """
        Rule = self.env["ir.rule"].sudo()
        eval_context = Rule._eval_context()
        owned = set()
        for rule in Rule.search([("active", "=", True)]):
            if not rule.domain_force:
                continue
            leaves = []
            with contextlib.suppress(Exception):
                # A rule this test cannot evaluate is not a rule it can credit.
                leaves = safe_eval(rule.domain_force, dict(eval_context))
            for leaf in leaves:
                if (
                    isinstance(leaf, list | tuple)
                    and len(leaf) == 3
                    and leaf[0] == "create_uid"
                    and leaf[1] == "="
                    and leaf[2] == self.env.uid
                ):
                    owned.add(rule.model_id.model)
        return owned

    def test_every_transient_model_is_scoped_to_its_creator(self):
        """The structural sweep, which needs no fixture and so reaches bridges.

        A transient record is one user's working state. Any of them readable by
        a second user is a finding, wherever it is declared -- this is what
        turned up `document.transfer.register` and its lines in
        `document_physical`, whose ACL opens them to every documents user.
        """
        self.assertFalse(
            self._wizard_models() - self._owner_rule_models(),
            "these transient models carry no rule restricting rows to the user "
            "who created them, so one user's open wizard is another's record",
        )

    def test_the_roster_and_the_fixtures_agree(self):
        """The behavioural sweep below covers this module's own wizards.

        A wizard declared elsewhere is covered structurally by the test above;
        building one here would mean this module owning another's fixtures.
        """
        own = {
            name
            for name in self._wizard_models()
            if self.env[name]._original_module == "document"
        }
        self.assertTrue(own, "the sweep must find this module's wizards at all")
        self.assertFalse(
            own - set(self._builders()),
            "these wizards are declared by `document` and have no fixture "
            "below, so nothing checks that one user cannot reach another's",
        )

    def test_a_stranger_reaches_no_wizard_of_another_user(self):
        """The sweep: for every wizard, a read and a write by someone else."""
        reachable = []
        for model, build in self._builders().items():
            if model not in self._wizard_models():
                continue
            record = build(self.owner_env)
            self.env.flush_all()
            self.env.invalidate_all()
            stranger = self.stranger_env[model].browse(record.id)
            with self.subTest(model=model, operation="read"):
                try:
                    stranger.read(["create_uid"])
                    reachable.append(f"{model} (read)")
                except AccessError:
                    pass
            self.env.invalidate_all()
            with self.subTest(model=model, operation="write"):
                try:
                    stranger.write({"create_date": stranger.create_date})
                    reachable.append(f"{model} (write)")
                except AccessError:
                    pass
        self.assertFalse(
            reachable, f"another user's live wizard was reachable: {reachable}"
        )

    def test_the_owner_still_reaches_their_own_wizard(self):
        """Negative control: a rule that refused everyone would pass the sweep."""
        unreachable = []
        for model, build in self._builders().items():
            if model not in self._wizard_models():
                continue
            record = build(self.owner_env)
            self.env.flush_all()
            self.env.invalidate_all()
            try:
                self.owner_env[model].browse(record.id).read(["create_uid"])
            except AccessError:
                unreachable.append(model)
        self.assertFalse(
            unreachable, f"the owner lost access to their own wizard: {unreachable}"
        )

    def test_a_stranger_cannot_read_a_pending_sharing_invitation(self):
        """The concrete case, spelled out: who you are about to share with."""
        document = self.owner_env["document.document"].create(
            {
                "name": "owner-private.txt",
                "type": "binary",
                "raw": b"p",
                "access_internal": "none",
                "access_via_link": "none",
            }
        )
        wizard = self.owner_env["document.sharing"].browse(
            self.owner_env["document.sharing"].action_open(document.ids)["res_id"]
        )
        wizard.invite_partner_ids = [Command.set(self.counterparty.ids)]
        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            self.stranger_env["document.sharing"].browse(
                wizard.id
            ).invite_partner_ids.mapped("name")

    def test_a_stranger_cannot_raise_the_role_of_a_pending_invitation(self):
        """The half that changes an outcome rather than merely revealing one."""
        document = self.owner_env["document.document"].create(
            {"name": "owner-private2.txt", "type": "binary", "raw": b"p"}
        )
        wizard = self.owner_env["document.sharing"].browse(
            self.owner_env["document.sharing"].action_open(document.ids)["res_id"]
        )
        self.assertEqual(wizard.invite_role, "view")
        self.env.flush_all()
        self.env.invalidate_all()

        with self.assertRaises(AccessError):
            self.stranger_env["document.sharing"].browse(wizard.id).write(
                {"invite_role": "edit"}
            )

        wizard.invalidate_recordset()
        self.assertEqual(wizard.invite_role, "view", "and nothing moved")
