from odoo.tests.common import tagged
from odoo.exceptions import ValidationError
from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nInCompany(L10nInTestInvoicingCommon):

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

    def test_l10n_in_cash_rounding_created_per_company(self):
        """
        Each IN company must have its own `Half Up` cash rounding record
        Creating a new IN company must not reassign the existing record
        """
        in_company = self._create_company(country_code='IN')
        in_cash_rounding_ids = self.env['account.cash.rounding'].search([
            ('name', '=', 'Half Up'), ('company_id.partner_id.country_code', '=', 'IN')
        ])
        self.assertRecordValues(in_cash_rounding_ids, [
            {'company_id': self.env.company.id},
            {'company_id': in_company.id},
        ])
