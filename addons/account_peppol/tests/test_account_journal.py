from odoo.exceptions import ValidationError
from odoo.tests.common import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install')
class TestPeppolAccountJournal(AccountTestInvoicingCommon):

    def test_peppol_journal_type_change(self):
        self.env.company.write({"account_peppol_proxy_state": "active"})
        journal = self.env.company.peppol_purchase_journal_id
        self.assertTrue(journal)
        with self.assertRaises(ValidationError):
            journal.write({"type": "sale"})

        other_journal = self.env['account.journal'].create({
            'name': "Other purchase journal",
            'code': "OPJ",
            'type': 'purchase',
        })
        other_journal.write({"type": "sale"})
        self.assertEqual(other_journal.type, 'sale')
