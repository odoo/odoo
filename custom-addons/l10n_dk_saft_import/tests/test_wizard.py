# Part of Odoo. See LICENSE file for full copyright and licensing details.

from base64 import b64encode

from odoo.tests import tagged
from odoo.tools import file_open
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('-at_install', 'post_install_l10n', 'post_install')
class AccountTestSAFTImport(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        cls.chart_template = chart_template_ref or 'dk'
        super().setUpClass(cls.chart_template)

        cls.company = cls.setup_company_data('SAF-T test company', chart_template=cls.chart_template)['company']
        cls.env.user.write({
            'company_ids': [cls.company.id],
            'company_id': cls.company.id,
        })

        cls.currency = cls.env.ref('base.DKK')

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
        journals = self.env['account.journal'].search([('code', 'like', 'SAF%')])
        self.assertTrue(len(journals.ids) == 3, "Journal creation failed")

        # Check partners
        file_partners = ['Azure Interior', 'Beautiful partner', 'Deco Addict']
        partners = self.env['res.partner'].search([('name', 'in', file_partners)])
        self.assertEqual(file_partners, partners.mapped('name'), "Partners creation failed")

        moves = self.env['account.move'].search(self.env['account.move']._check_company_domain(self.env.company))
        self.assertEqual(len(moves), 13, "Move import failed")
        self.assertEqual(
            sum(self.env['account.move'].search(self.env['account.move']._check_company_domain(self.env.company)).line_ids.mapped('debit')),
            276762.5,
            "Move debit amount imported is wrong"
        )

        self.assertEqual(
            len(self.env['account.move'].search(self.env['account.move']._check_company_domain(self.env.company)).line_ids.mapped('tax_ids')),
            1, "The tax is put on the move imported"
        )
