# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.addons.account_edi.tests.common import AccountEdiTestCommon

from .common import TestSaEdiCommon

_logger = logging.getLogger(__name__)


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestSAEdiAccountMove(TestSaEdiCommon):

    @classmethod
    @AccountEdiTestCommon.setup_edi_format('l10n_sa_edi.edi_sa_zatca')
    @AccountEdiTestCommon.setup_country('sa')
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_branches()

    @classmethod
    def _setup_branches(cls):
        cls.sa_branch = cls.env['res.company'].create({
            'name': 'SA Branch',
            'parent_id': cls.company.id,
            'country_id': cls.company.country_id.id,
        })

    def test_invoice_with_mismatched_companies(self):
        move_data = {
            'name': 'INV/2025/00012',
            'invoice_date': '2025-07-05',
            'invoice_date_due': '2025-07-12',
            'partner_id': self.partner_sa,
            'invoice_line_ids': [{
                'product_id': self.product_a.id,
                'price_unit': self.product_a.standard_price,
                'quantity': 1,
                'tax_ids': self.tax_15.ids,
            }]
        }

        invoice = self._create_invoice(**move_data)
        invoice.company_id = self.sa_branch

        with self.assertRaises(UserError, msg="A UserError is expected when the company on the invoice doesn't match the company on the journal."):
            invoice.action_post()
