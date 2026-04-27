from odoo.addons.account_reports.tests.account_sales_report_common import AccountSalesReportCommon


class CzechReportsCommon(AccountSalesReportCommon):
    @classmethod
    @AccountSalesReportCommon.setup_country('cz')
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_eu_1 = cls.env['res.partner'].create({
            'name': 'Partner EU 1',
            'country_id': cls.env.ref('base.fr').id,
            'vat': 'FR23334175221',
        })
        cls.partner_eu_2 = cls.env['res.partner'].create({
            'name': 'Partner EU 2',
            'country_id': cls.env.ref('base.de').id,
            'vat': 'DE123456788',
        })
        cls.partner_eu_3 = cls.env['res.partner'].create({
            'name': 'Partner EU 3',
            'country_id': cls.env.ref('base.be').id,
            'vat': 'BE0477472701',
        })

        cls.partner_cz_1 = cls.env['res.partner'].create({
            'name': 'Partner CZ 1',
            'country_id': cls.env.ref('base.cz').id,
            'vat': 'CZ00000001',
            'is_company': True,
        })

        cls.partner_cz_2 = cls.env['res.partner'].create({
            'name': 'Partner CZ 2',
            'country_id': cls.env.ref('base.cz').id,
            'vat': 'CZ11111119',
            'is_company': True,
        })

        cls.partner_non_eu = cls.env['res.partner'].create({
            'name': 'Partner Non-EU',
            'country_id': cls.env.ref('base.br').id,
            'is_company': True,
        })

        cls.company_id = cls.env.company.id
        # Sale Taxes
        cls.l10n_cz_21_domestic_supplies = cls.env.ref(f'account.{cls.company_id}_l10n_cz_21_domestic_supplies')
        cls.l10n_cz_12_domestic_supplies = cls.env.ref(f'account.{cls.company_id}_l10n_cz_12_domestic_supplies')
        cls.l10n_cz_tax_reverse_charge_mode = cls.env.ref(f'account.{cls.company_id}_l10n_cz_tax_reverse_charge_mode')
        cls.l10n_cz_investment_gold = cls.env.ref(f'account.{cls.company_id}_l10n_cz_investment_gold')
        # Purchase Taxes
        cls.l10n_cz_21_receipt_domestic_supplies = cls.env.ref(f'account.{cls.company_id}_l10n_cz_21_receipt_domestic_supplies')
        cls.l10n_cz_12_receipt_domestic_supplies = cls.env.ref(f'account.{cls.company_id}_l10n_cz_12_receipt_domestic_supplies')
        cls.l10n_cz_21_tax_reverse_charge_scheme = cls.env.ref(f'account.{cls.company_id}_l10n_cz_21_tax_reverse_charge_scheme')
        cls.l10n_cz_12_tax_reverse_charge_scheme = cls.env.ref(f'account.{cls.company_id}_l10n_cz_12_tax_reverse_charge_scheme')
        cls.l10n_cz_21_acquisition_goods_eu = cls.env.ref(f'account.{cls.company_id}_l10n_cz_21_acquisition_goods_eu')
        cls.l10n_cz_12_purchase_goods_eu = cls.env.ref(f'account.{cls.company_id}_l10n_cz_12_purchase_goods_eu')
        cls.l10n_cz_21_receipt_service_person_eu = cls.env.ref(f'account.{cls.company_id}_l10n_cz_21_receipt_service_person_eu')
        cls.l10n_cz_12_receipt_service_person_eu = cls.env.ref(f'account.{cls.company_id}_l10n_cz_12_receipt_service_person_eu')
        cls.l10n_cz_acquisition_transport = cls.env.ref(f'account.{cls.company_id}_l10n_cz_acquisition_transport')
        cls.l10n_cz_21_receipt_service_person_non_eu = cls.env.ref(f'account.{cls.company_id}_l10n_cz_21_receipt_service_person_non_eu')
        cls.l10n_cz_12_receipt_service_person_non_eu = cls.env.ref(f'account.{cls.company_id}_l10n_cz_12_receipt_service_person_non_eu')

        cls.company.update({
            'country_id': cls.env.ref('base.cz').id,
            'vat': 'CZ12345679',
            'l10n_cz_tax_office_id': cls.env.ref('l10n_cz_reports_2025.tax_office_1'),
            'email': 'info@company.czexample.com',
        })
