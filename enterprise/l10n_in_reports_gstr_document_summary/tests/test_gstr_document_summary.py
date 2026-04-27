# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, timedelta

from odoo.tests import tagged
from odoo.addons.l10n_in_reports_gstr.tests.common import L10nInTestAccountGstReportsCommon

TEST_DATE = date(2025, 5, 20)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestDocumentSummary(L10nInTestAccountGstReportsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_b.write({
            'l10n_in_gst_treatment': 'regular',
            'street': 'Test Street',
            'city': 'Mumbai',
        })
        cls.product_a.write({'l10n_in_hsn_code': '998877'})

    def test_gstr1_doc_issue(self):
        invoice = self._init_inv(
            partner=self.partner_b,
            taxes=self.comp_igst_18,
            line_vals={'price_unit': 500, 'quantity': 1},
            invoice_date=TEST_DATE,
        )
        return_period = self.env['l10n_in.gst.return.period'].create({
            'company_id': self.default_company.id,
            'periodicity': 'monthly',
            'year': TEST_DATE.strftime('%Y'),
            'month': TEST_DATE.strftime('%m'),
            'start_date': TEST_DATE.replace(day=1),
            'end_date': (TEST_DATE.replace(day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1),
        })
        return_period.action_generate_document_summary()
        gstr1_json = return_period._get_gstr1_json()
        expected_doc_issue = {
            'doc_det': [
                {
                    'doc_num': 1,
                    'docs': [
                        {
                            'num': 1,
                            'from': invoice.name,
                            'to': invoice.name,
                            'totnum': 1,
                            'cancel': 0,
                            'net_issue': 1,
                        }
                    ]
                }
            ]
        }
        self.assertEqual(gstr1_json.get('doc_issue'), expected_doc_issue)
