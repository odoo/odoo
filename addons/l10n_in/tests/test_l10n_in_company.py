from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nInCompany(L10nInTestInvoicingCommon):

    _test_groups = None  # FIXME list needed groups

    def test_l10n_in_journal_priority(self):
        """
        Ensure that when a branch company has its own journals,
        it is selected instead of falling back to the parent company's journal.
        """
        # Create a branch company under the default company
        self.company_data['company'].write({
            'child_ids': [Command.create({
                'name': 'IN Branch',
                'country_id': self.country_in.id,
                'vat': '24FANCY1234AAZA',
            })],
        })
        self.in_branch = self.company_data['company'].child_ids

        # Check: branch has no journal initially
        branch_sale_journal = self.env['account.journal'].search([
            ('company_id', '=', self.in_branch.id),
            ('type', '=', 'sale'),
        ], limit=1)
        self.assertFalse(branch_sale_journal)

        # Load the chart template for the branch (creates branch journals)
        self._use_chart_template(self.in_branch)

        # After branch journal, Ensure branch and parent
        # companies select their respective journals.
        branch_invoice = self._create_invoice(company_id=self.in_branch.id)
        parent_company_invoice = self._create_invoice(company_id=self.default_company.id)
        self.assertEqual(self.in_branch.id, branch_invoice.journal_id.company_id.id)
        self.assertEqual(self.default_company.id, parent_company_invoice.journal_id.company_id.id)

    def test_l10n_in_audit_trail(self):
        """Audit trail behavior for Indian companies:
        - Can be enabled/disabled when no accounting entries exist
        - Cannot be disabled once entries exist
        """
        in_company = self._create_company(country_code='IN')

        # No accounting entries → audit trail should be freely toggleable
        self.assertFalse(in_company.root_id._existing_accounting())
        in_company.restrictive_audit_trail = True
        in_company.restrictive_audit_trail = False
        self.assertFalse(in_company.restrictive_audit_trail)

        # Create and post an invoice to generate an accounting entry
        self._create_invoice_one_line(
            product_id=self.product_a,
            invoice_payment_term_id=self.pay_terms_b,
            post=True,
            company_id=in_company,
        )
        self.assertTrue(in_company.root_id._existing_accounting())
        in_company.restrictive_audit_trail = True

        # We get incorrect force_restrictive_audit_trail if we don't invalidate the cache,
        in_company.invalidate_recordset(fnames=['force_restrictive_audit_trail'])

        # Disabling audit trail should fail
        with self.assertRaises(ValidationError):
            in_company.restrictive_audit_trail = False

        # Audit Trail should remain True
        self.assertTrue(in_company.restrictive_audit_trail)
