# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install_l10n', 'post_install')
class AccountTestSAFTImport(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('dk')
    def setUpClass(cls):
        super().setUpClass()

        cls.company.write({'name': 'SAF-T test company'})

        with file_open('l10n_dk_saft_import/tests/data/saft_example_dk.xml') as f:
            cls.saft_filedata = b64encode(f.read().encode())

        # Accounts codes that should be present after import of the SAF-T example file
        cls.reference_accounts = {
            "1500", "19201", "19202", "2400", "2701", "2711", "3000", "4000", "999999"
        }

    #############################
    #       Test methods        #
    #############################

    def test_saft_import(self, wizard=False):
        wizard = wizard or self.env['account.saft.import.wizard'].create({
            'attachment_id': self.saft_filedata,
        })
        wizard.action_import()

        # Check journals
        journals = self.env['account.journal'].search([('code', 'like', 'JOU%')])
        self.assertTrue(len(journals.ids) == 3, "Journal creation failed")

        # Check partners
        file_partners = ['Acme Corporation', 'Azure Interior', 'Beautiful partner']
        partners = self.env['res.partner'].search([('name', 'in', file_partners)])
        self.assertEqual(file_partners, partners.mapped('name'), "Partners creation failed")

        moves = self.env['account.move'].search(self.env['account.move']._check_company_domain(self.env.company))
        self.assertEqual(len(moves), 12, "Move import failed")
        self.assertEqual(
            sum(self.env['account.move'].search(self.env['account.move']._check_company_domain(self.env.company)).line_ids.mapped('debit')),
            276762.5,
            "Move debit amount imported is wrong"
        )

        self.assertEqual(
            len(self.env['account.move'].search(self.env['account.move']._check_company_domain(self.env.company)).line_ids.mapped('tax_ids')),
            1, "The tax is put on the move imported"
        )
