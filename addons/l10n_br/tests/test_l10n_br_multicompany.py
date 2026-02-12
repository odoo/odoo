from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import Command
import logging
_logger = logging.getLogger(__name__)
@tagged("post_install_l10n", "post_install", "-at_install")
class TestL10nBrMultiCompany(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('br')
    def setUpClass(cls):
        super().setUpClass()

    def test_multicompany_fiscal_position(self):
        default_company = self.env['res.company'].browse(1)
        br_company = self.company_data["company"]
        self.env.user.write({
            'company_ids': [Command.link(default_company.id)]
        })
        fpos1 = self.env["account.fiscal.position"].sudo().create(
            {
                "name": default_company.name,
                "company_id": default_company.id,
            }
        )
        fpos2 = self.env["account.fiscal.position"].create(
            {
                "name": br_company.name,
                "company_id": br_company.id,
            }
        )
        self.partner_a.with_company(br_company).write(
            {
                'property_account_position_id': fpos2.id,
                'country_id': br_company.country_id.id
            }
        )
        self.partner_a.sudo().with_company(default_company).write({'property_account_position_id': fpos1.id})
        
        test_move = self.env['account.move'].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "company_id": br_company.id
            }
        )

        self.assertEqual(test_move.fiscal_position_id, fpos2)
