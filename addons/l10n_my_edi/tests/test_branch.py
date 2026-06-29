# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nMyEdiBranch(AccountTestInvoicingCommon):

    _test_groups = None  # FIXME list needed groups

    @classmethod
    @AccountTestInvoicingCommon.setup_country('my')
    def setUpClass(cls):
        super().setUpClass()

        cls.company_data['company'].write({
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
        })

        cls.branch_company = cls.env['res.company'].create({
            'name': 'MY Branch Company',
            'parent_id': cls.company_data['company'].id,
            'country_id': cls.env.ref('base.my').id,
            'account_fiscal_country_id': cls.env.ref('base.my').id,
            'vat': 'C2584563200',
            'l10n_my_edi_mode': 'test',
        })
        cls.branch_company.write({
            'l10n_my_identification_type': 'BRN',
            'l10n_my_identification_number': '202001234567',
        })

        cls.proxy_user = cls.env['account_edi_proxy_client.user']._register_proxy_user(
            cls.company_data['company'], 'l10n_my_edi', 'demo',
        )
        cls.proxy_user.edi_mode = 'test'

    def test_branch_detection(self):
        """ A child company sharing VAT, identification number, and country with parent is a branch. """
        self.assertTrue(self.branch_company.l10n_my_edi_is_branch)

    def test_non_branch_different_vat(self):
        """ A child company with a different VAT is not considered a branch. """
        self.branch_company.vat = 'C9999999999'
        self.assertFalse(self.branch_company.l10n_my_edi_is_branch)

    def test_branch_inherits_proxy_user(self):
        """ Branch inherits the proxy user from its parent company. """
        self.assertEqual(self.branch_company.l10n_my_edi_proxy_user_id, self.proxy_user)

    def test_sole_proprietor_proxy_identification(self):
        """ Sole proprietor identification returns TIN:BRN format. """
        company = self.company_data['company']
        company.l10n_my_edi_is_sole_proprietor = True
        identification = self.env['account_edi_proxy_client.user']._get_proxy_identification(
            company, 'l10n_my_edi',
        )
        self.assertEqual(identification, 'C2584563200:202001234567')
