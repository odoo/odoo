from odoo import Command
from odoo.tests import tagged

from odoo.addons.l10n_pt_certification.tests.test_taxes_tax_totals_summary import TestTaxesTaxTotalsSummaryL10nPt
from odoo.addons.sale.tests.common import TestTaxCommonSale
from odoo.addons.account.tests.common import TestTaxCommon


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestL10nPtTaxTotalsSummarySale(TestTaxCommonSale, TestTaxesTaxTotalsSummaryL10nPt):

    @classmethod
    @TestTaxCommon.setup_country('pt')
    def setUpClass(cls):
        super().setUpClass()
        cls.env['l10n_pt.at.series'].create({
            'name': 'Test',
            'company_id': cls.company_data['company'].id,
            'training_series': True,
            'at_series_line_ids': [
                Command.create({'type': 'quotation', 'prefix': 'OR', 'at_code': 'AT-TESTQUOT'}),
                Command.create({'type': 'sales_order', 'prefix': 'NE', 'at_code': 'AT-TESTSO'}),
            ],
        })

    def test_taxes_l10n_pt_sale_orders(self):
        for test_index, document, expected_values in self._test_taxes_l10n_pt():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)
