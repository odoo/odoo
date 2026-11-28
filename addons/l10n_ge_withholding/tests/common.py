from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nGeWithholdingCommon(AccountTestInvoicingCommon):
    @classmethod
    @AccountTestInvoicingCommon.setup_country('ge')
    def setUpClass(cls):
        super().setUpClass()
        company = cls.company_data['company']
        company.withholding_tax_base_account_id = cls.env['account.account'].create({'code': 'WITHB', 'name': "Withholding Tax Base Account", 'account_type': 'asset_current'})
        cls.outstanding_account = cls.env['account.account'].create({'code': 'OSTP420', 'name': "Outstanding Payments", 'account_type': 'asset_current'})
        withholding_sequence = cls.env['ir.sequence'].create({'implementation': 'no_gap', 'name': "Withholding Sequence", 'padding': 4, 'number_increment': 1})
        chart_template = cls.env['account.chart.template'].with_company(company)
        cls.tax_services = chart_template.ref('ge_tax_wh_10_s')
        cls.tax_dividends = chart_template.ref('ge_tax_wh_5_d')
        cls.tax_interest = chart_template.ref('ge_tax_wh_5_i')
        (cls.tax_services + cls.tax_dividends + cls.tax_interest).withholding_sequence_id = withholding_sequence

    def _register_payment(self, bills, **vals):
        wizard = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=bills.ids).create(vals)
        wizard.withholding_outstanding_account_id = self.outstanding_account
        return wizard

    def _get_tag(self, name):
        tag = self.env['account.account.tag'].search([('name', '=', name), ('country_id.code', '=', 'GE')])
        tag.ensure_one()
        return tag
