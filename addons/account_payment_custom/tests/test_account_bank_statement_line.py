# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.account_payment_custom.tests.common import AccountPaymentCustomCommon


@tagged("-at_install", "post_install")
class TestAccountBankStatementLine(AccountPaymentCustomCommon):
    def test_matching_statement_line_confirms_wire_transfer_transaction(self):
        """Test that wire transfer transactions are confirmed when a matching bank statement line
        is found."""
        tx = self._create_transaction(flow="direct", state="pending")
        absl = self.env["account.bank.statement.line"].create({
            "payment_ref": tx.reference,
            "partner_id": tx.partner_id.id,
            "amount": tx.amount,
        })
        absl._cron_confirm_wire_transfer_transactions()
        self.assertEqual(tx.state, "done")

    def test_non_matching_statement_line_does_not_confirm_wire_transfer_transaction(self):
        """Test that wire transfer transactions are not confirmed with a non-matching bank statement
        line."""
        tx = self._create_transaction(flow="direct", state="pending")
        absl = self.env["account.bank.statement.line"].create({
            "payment_ref": "S00098",  # non-matching reference
            "partner_id": tx.partner_id.id,
            "amount": tx.amount,
        })
        absl._cron_confirm_wire_transfer_transactions()
        self.assertEqual(tx.state, "pending")
