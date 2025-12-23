from odoo import Command
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nInCompany(L10nInTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create a branch company under the default company
        cls.company_data['company'].write({
            'child_ids': [Command.create({
                'name': 'IN Branch',
                'country_id': cls.country_in.id,
                'vat': '24FANCY1234AAZA',
            })],
        })
        cls.in_branch = cls.company_data['company'].child_ids

    def test_l10n_in_journal_priority(self):
        """
        Ensure that when a branch company has its own journals,
        it is selected instead of falling back to the parent company's journal.
        """

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
