import markupsafe

from lxml import etree

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.modules import get_module_path
from odoo.tests import tagged
from odoo.tools.misc import file_open


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestCisXML(AccountTestInvoicingCommon):
    def get_test_credentials(self):
        return {
            'sender_id': 'CISRUSER1033',
            'password': markupsafe.Markup("fGuR34fAOEJf"),
            'tax_office_number': '123',
            'tax_office_reference': 'R234',
        }

    def get_xml_from_test_file(self, path_from_test_dir):
        """
        Reads an XML document from the test directory accordingly to the path provided in params and returns it as an XML tree
        """
        module_path = get_module_path('l10n_uk_reports_cis')
        test_dir = f'{module_path}/tests'
        return etree.XML(file_open(f'{test_dir}/{path_from_test_dir}', 'rb').read())

    def test_xml_gen_without_partners(self):
        transaction_create_vals = {
            'transaction_type': 'cis_monthly_return',
            'company_id': self.env.company.id,
            'period_start': '2009-04-06',
            'period_end': '2009-05-05',
            'sender_user_id': self.env.user.id,
        }
        self.env.company.l10n_uk_hmrc_unique_taxpayer_reference = '2325648152'
        self.env.company.l10n_uk_hmrc_account_office_reference = '123PP07654321'
        self.env.company.partner_id.is_company = False

        transaction = self.env['l10n_uk.hmrc.transaction'].create(transaction_create_vals)
        xml_data = transaction._generate_cis_mr_xml_data(
            self.get_test_credentials(),
            {
                'inactivity_indicator': False,
                'subcontractor_return_ids': [],
                'subcontractor_ids': [],
                'subcontractor_verification': False,
                'employment_status': False,
            }
        )
        report = transaction._generate_xml_document(xml_data)
        self.assertXmlTreeEqual(etree.XML(report), self.get_xml_from_test_file('hmrc_documents/cis_return_request_scenario_1.xml'))

    def test_xml_gen_with_partners(self):
        transaction_create_vals = {
            'transaction_type': 'cis_monthly_return',
            'company_id': self.env.company.id,
            'period_start': '2009-04-06',
            'period_end': '2009-05-05',
            'sender_user_id': self.env.user.id,
        }
        self.env.company.l10n_uk_hmrc_unique_taxpayer_reference = '7325648155'
        self.env.company.l10n_uk_hmrc_account_office_reference = '123PP87654321'
        self.env.company.partner_id.is_company = False

        transaction = self.env['l10n_uk.hmrc.transaction'].create(transaction_create_vals)
        partner_a = self.env['res.partner'].create({
            'name': 'John Peter Brown',
            'is_company': False,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V6499876214A',
            'l10n_uk_reports_cis_deduction_rate': 'unmatched',
            'l10n_uk_reports_cis_forename': 'John',
            'l10n_uk_reports_cis_second_forename': 'Peter',
            'l10n_uk_reports_cis_surname': 'Brown',
        })

        partner_b = self.env['res.partner'].create({
            'name': 'TA Plumbing',
            'is_company': True,
            'l10n_uk_cis_enabled': True,
            'l10n_uk_reports_cis_verification_number': 'V8745678309AA',
            'l10n_uk_reports_cis_deduction_rate': 'unmatched',
        })

        xml_data = transaction._generate_cis_mr_xml_data(
            self.get_test_credentials(),
            {
                'inactivity_indicator': True,
                'subcontractor_return_ids': [
                    {
                        'id': partner_a.id,
                        'total_payment_made': 2000,
                        'direct_cost_of_materials': 500,
                        'total_amount_deducted': 450,
                    },
                    {
                        'id': partner_b.id,
                        'total_payment_made': 2750,
                        'direct_cost_of_materials': 0,
                        'total_amount_deducted': 825,
                    },
                ],
                'subcontractor_ids': [partner_a.id, partner_b.id],
                'subcontractor_verification': True,
                'employment_status': True,
            }
        )
        # We need to set specific ids to subcontractors otherwise the irmark will not be the same and therefore be undeterministic
        xml_data['document']['subcontractors'][0]['id'] = 45
        xml_data['document']['subcontractors'][1]['id'] = 46
        xml_data['ir_mark'] = transaction._generate_ir_mark(xml_data)
        report = transaction._generate_xml_document(xml_data)
        self.assertXmlTreeEqual(etree.XML(report), self.get_xml_from_test_file('hmrc_documents/cis_return_request_scenario_3.xml'))
