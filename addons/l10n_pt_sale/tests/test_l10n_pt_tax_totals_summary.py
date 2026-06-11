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
        cls.env['l10n_pt.at.series'].create([{
            'name': 'Test',
            'company_id': cls.company_data['company'].id,
            'training_series': True,
            'date_start': '2024-01-01',
            'journal_id': cls.company_data['default_journal_sale'].id,
            'document_type': doc_type,
            'prefix': prefix,
            'at_code': f'AT-TEST{doc_type.upper().replace("_", "")[:4]}',
        } for doc_type, prefix in (('quotation', 'OR'), ('sales_order', 'NE'))])

    def test_taxes_l10n_pt_sale_orders(self):
        for test_index, document, expected_values in self._test_taxes_l10n_pt():
            with self.subTest(test_index=test_index):
                sale_order = self.convert_document_to_sale_order(document)
                self.assert_sale_order_tax_totals_summary(sale_order, expected_values)
