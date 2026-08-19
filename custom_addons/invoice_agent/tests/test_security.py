"""Security tests for invoice_agent: record rules + model ACLs.

Covered here:

* record rules: a reviewer restricted to company B raises ``AccessError``
  reading another company's bill, while a same-company reviewer can read it —
  the global ``account_move_comp_rule``
  (``[('company_id', 'in', company_ids)]``) filters recordsets, so
  ``check_access('read')`` fails even though the user holds the model-level
  read ACL through ``account.group_account_invoice`` (implied by
  ``invoice_agent.group_invoice_agent_user``).
* model ACLs on ``invoice.agent.extraction.line``: Agent Reviewer can read and
  write extraction lines but cannot create or delete them; Agent Manager can.
"""

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from .test_extraction import InvoiceAgentTestCommon

REVIEWER_GROUP = "invoice_agent.group_invoice_agent_user"
MANAGER_GROUP = "invoice_agent.group_invoice_agent_manager"


@tagged("post_install", "-at_install")
class TestInvoiceAgentSecurity(InvoiceAgentTestCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        # A bare company is enough: account_move_comp_rule is a *global* rule
        # ([('company_id', 'in', company_ids)]) that ANDs with the group's
        # see-all rules, so reviewer B (company_ids=[company_b]) is filtered
        # off a company-a bill even though company_b has no chart of accounts.
        cls.company_b = cls.env["res.company"].create({"name": "Company B"})

        cls.reviewer_a = new_test_user(
            cls.env,
            name="Reviewer A",
            login="reviewer_a",
            group_ids=[cls.env.ref(REVIEWER_GROUP).id],
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )
        cls.reviewer_b = new_test_user(
            cls.env,
            name="Reviewer B",
            login="reviewer_b",
            group_ids=[cls.env.ref(REVIEWER_GROUP).id],
            company_id=cls.company_b.id,
            company_ids=[(6, 0, [cls.company_b.id])],
        )
        cls.manager = new_test_user(
            cls.env,
            name="Manager",
            login="agent_manager",
            group_ids=[cls.env.ref(MANAGER_GROUP).id],
            company_id=cls.company_a.id,
            company_ids=[(6, 0, [cls.company_a.id])],
        )

        cls.bill_a = cls.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": cls.partner.id,
                "invoice_date": "2026-07-01",
                "journal_id": cls.purchase_journal.id,
                "ai_extraction_status": "extracted",
                "ai_confidence": 0.9,
            },
        )
        cls.env.flush_all()

    # ------------------------------------------------------------------
    # Record rules: multi-company confinement on account.move
    # ------------------------------------------------------------------
    def test_reviewer_of_other_company_cannot_read_bill(self):
        move = self.bill_a.with_user(self.reviewer_b)
        with self.assertRaises(AccessError):
            move.check_access("read")

    def test_reviewer_of_same_company_can_read_bill(self):
        move = self.bill_a.with_user(self.reviewer_a)
        # Must not raise.
        move.check_access("read")
        self.assertEqual(move.ai_extraction_status, "extracted")

    def test_superuser_can_read_any_bill(self):
        self.bill_a.with_user(self.env.uid).check_access("read")

    # ------------------------------------------------------------------
    # Model ACLs: invoice.agent.extraction.line
    # ------------------------------------------------------------------
    def _line_env(self, user):
        return self.env["invoice.agent.extraction.line"].with_user(user)

    def test_reviewer_can_read_and_write_but_not_create_lines(self):
        # Line must be created by Manager because Reviewer lacks create ACL
        line_as_manager = self._line_env(self.manager).create(
            {
                "move_id": self.bill_a.id,
                "field_name": "Total",
                "extracted_value": "100.00",
                "field_confidence": 0.9,
            },
        )

        # Switch context to Reviewer
        line = line_as_manager.with_user(self.reviewer_a)

        # Reviewer can read and write...
        line.check_access("read")
        line.check_access("write")
        line.field_confidence = 0.95
        self.assertAlmostEqual(line.field_confidence, 0.95, places=2)

        # ...but cannot create or delete (ir.model.access.csv: 0,0).
        with self.assertRaises(AccessError):
            line.check_access("create")
        with self.assertRaises(AccessError):
            line.check_access("unlink")

    def test_manager_can_create_and_delete_lines(self):
        line = self._line_env(self.manager).create(
            {
                "move_id": self.bill_a.id,
                "field_name": "Total",
                "extracted_value": "100.00",
                "field_confidence": 0.9,
            },
        )
        line.check_access("create")
        line.check_access("unlink")
        line.unlink()
        self.assertFalse(line.exists())
