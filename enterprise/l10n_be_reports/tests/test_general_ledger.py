# Part of Odoo. See LICENSE file for full copyright and licensing details.
from freezegun import freeze_time
from lxml import etree

from odoo import fields
from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class BelgiumGeneralLedgerTest(AccountSalesReportCommon):

    @classmethod
    @AccountSalesReportCommon.setup_country('be')
    def setUpClass(cls):
        super().setUpClass()
        cls.company.update({
            'vat': 'BE0477472701',
        })

    @freeze_time('2023-01-01')
    def test_annual_account_export(self):
        moves = self.env['account.move'].create([{
            'move_type': 'entry',
            'date': fields.Date.from_string('2023-01-01'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 1000.0, 'credit': 0.0, 'name': 'move_01_01',
                        'account_id': self.company_data['default_account_receivable'].id}),
                (0, 0, {'debit': 0.0, 'credit': 1000.0, 'name': 'move_01_02',
                        'account_id': self.company_data['default_account_revenue'].id}),
            ],
        }, {
            'move_type': 'entry',
            'date': fields.Date.from_string('2023-01-01'),
            'journal_id': self.company_data['default_journal_sale'].id,
            'line_ids': [
                (0, 0, {'debit': 250.0, 'credit': 0.0, 'name': 'move_02_01',
                        'account_id': self.company_data['default_account_payable'].id}),
                (0, 0, {'debit': 0.0, 'credit': 250.0, 'name': 'move_02_02',
                        'account_id': self.company_data['default_account_expense'].id}),
            ],
        }])
        moves.action_post()

        report = self.env.ref('account_reports.general_ledger_report')
        options = self._generate_options(report, '2023-01-01', '2023-01-01')
        annual_accounts_data = self.env[report.custom_handler_model_name].l10n_be_get_annual_accounts(options)
        actual_xml_root = etree.fromstring(annual_accounts_data['file_content'])

        receivable = self.company_data['default_account_receivable']
        revenue = self.company_data['default_account_revenue']
        payable = self.company_data['default_account_payable']
        expense = self.company_data['default_account_expense']

        expected_xml = f"""
            <TussentijdseStaat>
                <Versie>1.0</Versie>
                <Rekeningen>
                    <Rekening>
                        <DiverseOperatie></DiverseOperatie>
                        <RekeningNummer>{receivable.code}</RekeningNummer>
                        <BedragCredit>0.0</BedragCredit>
                        <BedragDebet>1000.0</BedragDebet>
                        <OmschrijvingNederlands>{receivable.name}</OmschrijvingNederlands>
                        <OmschrijvingFrans>{receivable.name}</OmschrijvingFrans>
                        <OmschrijvingEngels>{receivable.name}</OmschrijvingEngels>
                        <OmschrijvingDuits>{receivable.name}</OmschrijvingDuits>
                    </Rekening>
                    <Rekening>
                        <DiverseOperatie></DiverseOperatie>
                        <RekeningNummer>{payable.code}</RekeningNummer>
                        <BedragCredit>0.0</BedragCredit>
                        <BedragDebet>250.0</BedragDebet>
                        <OmschrijvingNederlands>{payable.name}</OmschrijvingNederlands>
                        <OmschrijvingFrans>{payable.name}</OmschrijvingFrans>
                        <OmschrijvingEngels>{payable.name}</OmschrijvingEngels>
                        <OmschrijvingDuits>{payable.name}</OmschrijvingDuits>
                    </Rekening>
                    <Rekening>
                        <DiverseOperatie></DiverseOperatie>
                        <RekeningNummer>{expense.code}</RekeningNummer>
                        <BedragCredit>250.0</BedragCredit>
                        <BedragDebet>0.0</BedragDebet>
                        <OmschrijvingNederlands>{expense.name}</OmschrijvingNederlands>
                        <OmschrijvingFrans>{expense.name}</OmschrijvingFrans>
                        <OmschrijvingEngels>{expense.name}</OmschrijvingEngels>
                        <OmschrijvingDuits>{expense.name}</OmschrijvingDuits>
                    </Rekening>
                    <Rekening>
                        <DiverseOperatie></DiverseOperatie>
                        <RekeningNummer>{revenue.code}</RekeningNummer>
                        <BedragCredit>1000.0</BedragCredit>
                        <BedragDebet>0.0</BedragDebet>
                        <OmschrijvingNederlands>{revenue.name}</OmschrijvingNederlands>
                        <OmschrijvingFrans>{revenue.name}</OmschrijvingFrans>
                        <OmschrijvingEngels>{revenue.name}</OmschrijvingEngels>
                        <OmschrijvingDuits>{revenue.name}</OmschrijvingDuits>
                    </Rekening>
                </Rekeningen>
                <Datum>2023-01-01</Datum>
                <Omschrijving>Annual Balance Report</Omschrijving>
                <Herkomst>Odoo</Herkomst>
            </TussentijdseStaat>
            """

        self.assertXmlTreeEqual(actual_xml_root, etree.fromstring(expected_xml))
