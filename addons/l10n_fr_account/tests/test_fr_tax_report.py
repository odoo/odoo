from odoo import Command
from odoo.tests.common import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestFrTaxReport(AccountTestInvoicingCommon):

    def test_t_taxes_balance_check_no_warning(self):
        """
        Verify that the French tax report raises no warning when T1-T7 taxes are used.
        The report's check compares the sum of A-boxes against the sum of T-base boxes;
        both sides must balance for the warning to be absent.
        Each T-tax shares the `A1` base tag, which is what links them to the A-box totals.
        T7's percent (5.0) is arbitrary as it has no predefined value in the localization.
        """
        fr = self.env.ref('base.fr')
        a_base = self.env['account.account.tag']._get_tax_tags('A1', fr.id)

        def _create_t_tax(name, percent):
            tag_t_base = self.env['account.account.tag']._get_tax_tags(f'{name}_base', fr.id) | a_base
            tag_t_tax = self.env['account.account.tag']._get_tax_tags(f'{name}_taxe', fr.id)
            return self.percent_tax(
                percent,
                name=f'{name}_tax',
                invoice_repartition_line_ids=[
                    Command.create({'repartition_type': 'base', 'tag_ids': [Command.set(tag_t_base.ids)]}),
                    Command.create({'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id, 'tag_ids': [Command.set(tag_t_tax.ids)]}),
                ],
                refund_repartition_line_ids=[
                    Command.create({'repartition_type': 'base', 'tag_ids': [Command.set(tag_t_base.ids)]}),
                    Command.create({'repartition_type': 'tax', 'account_id': self.company_data['default_account_tax_sale'].id, 'tag_ids': [Command.set(tag_t_tax.ids)]}),
                ],
            )

        t_taxes_data = [('T1', 1.75), ('T2', 1.05), ('T3', 10.0), ('T4', 2.1), ('T5', 0.9), ('T6', 2.1), ('T7', 5.0)]
        t_taxes = [_create_t_tax(tax_name, tax_percent) for tax_name, tax_percent in t_taxes_data]
        for tax in t_taxes:
            self._create_invoice(date="2019-01-01", invoice_line_ids=[self._prepare_invoice_line(price_unit=1000, tax_ids=tax)], post=True)

        report = self.env.ref('l10n_fr_account.tax_report').with_company(self.company_data['company'])
        options = report.get_options({
            'date': {
                'date_from': '2019-01-01',
                'date_to': '2019-01-31',
            }
        })
        report_information = report.get_report_information(options)
        self.assertNotIn('l10n_fr_reports.tax_report_warning_checks', report_information['warnings'])
