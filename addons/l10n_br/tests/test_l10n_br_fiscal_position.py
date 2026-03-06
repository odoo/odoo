# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBrFiscalPosition(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('br')
    def setUpClass(cls):
        super().setUpClass()
        cls.br_company = cls.company_data['company']

    def test_get_fiscal_position_multicompany(self):
        """When a partner has a fiscal position on both a BR company and
        another (non-BR) company, calling _get_fiscal_position from the BR company
        should return the BR fiscal position, not the one from the other company."""

        other_company = self.env['res.company'].create({
            'name': 'Other Company',
            'country_id': self.env.ref('base.us').id,
        })
        other_fp = self.env['account.fiscal.position'].create({
            'name': 'Other Company FP',
            'company_id': other_company.id,
            'sequence': 1,
        })
        br_fp = self.env['account.fiscal.position'].create({
            'name': 'BR Manual FP',
            'company_id': self.br_company.id,
            'sequence': 2,
        })
        partner = self.env['res.partner'].with_company(other_company).create({
            'name': 'Test Partner',
            'country_id': self.env.ref('base.br').id,
            'property_account_position_id': other_fp.id,
        })

        partner.with_company(self.br_company).property_account_position_id = br_fp

        fiscal_position = self.env['account.fiscal.position'].with_company(self.br_company)._get_fiscal_position(partner)

        self.assertEqual(
            fiscal_position, br_fp,
            "Should return the  BR fiscal position, not the fiscal position from another company",
        )
