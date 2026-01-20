from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestUblCiiCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=None)
        cls.partner_be = cls._create_partner_be()
        cls.partner_lu_dig = cls._create_partner_lu_dig()
        cls.partner_au = cls._create_partner_au()

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        # EXTENDS 'account'
        kwargs.setdefault('currency_id', cls.env.ref('base.EUR').id)
        results = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        company = results['company']
        company.tax_calculation_rounding_method = 'round_globally'
        return results

    @classmethod
    def _create_partner_be(cls, **kwargs):
        return cls.env['res.partner'].create({
            'name': 'partner_be',
            'street': "Rue des Bourlottes 9",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0477472701',
            'company_registry': '0477472701',
            'ubl_cii_format': None,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': cls.company_data['company'].id,
            'bank_ids': [Command.create({'acc_number': 'BE90735788866632'})],
            'country_id': cls.env.ref('base.be').id,
            **kwargs,
        })

    @classmethod
    def _create_partner_lu_dig(cls, **kwargs):
        return cls.env['res.partner'].create({
            'name': "Division informatique et gestion",
            'street': "bd de la Foire",
            'zip': "L-1528",
            'city': "Luxembourg",
            'vat': None,
            'ubl_cii_format': None,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': cls.company_data['company'].id,
            'country_id': cls.env.ref('base.lu').id,
            'peppol_eas': '9938',
            'peppol_endpoint': '00005000041',
            **kwargs,
        })

    @classmethod
    def _create_partner_au(cls, **kwargs):
        return cls.env['res.partner'].create({
            'name': "partner_au",
            'street': "Parliament Dr",
            'zip': "2600",
            'city': "Canberra",
            'vat': '53 930 548 027',
            'ubl_cii_format': None,
            'property_account_receivable_id': cls.company_data['default_account_receivable'].id,
            'property_account_payable_id': cls.company_data['default_account_payable'].id,
            'company_id': cls.company_data['company'].id,
            'country_id': cls.env.ref('base.au').id,
            'bank_ids': [Command.create({'acc_number': '93999574162167'})],
            **kwargs,
        })

    @classmethod
    def _create_mixed_early_payment_term(cls, **kwargs):
        return cls.env['account.payment.term'].create({
            'name': "2/7 Net 30",
            'note': "Payment terms: 30 Days, 2% Early Payment Discount under 7 days",
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 7,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
            **kwargs,
        })

    @classmethod
    def _create_add_invoice_line_cash_rounding(cls, **kwargs):
        return cls.env['account.cash.rounding'].create({
            'name': "Rounding 0.05",
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.company_data['default_account_revenue'].copy().id,
            'loss_account_id': cls.company_data['default_account_expense'].copy().id,
            'rounding_method': 'HALF-UP',
            **kwargs,
        })

    @classmethod
    def _create_biggest_tax_cash_rounding(cls, **kwargs):
        return cls.env['account.cash.rounding'].create({
            'name': "Rounding 0.05",
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'HALF-UP',
            **kwargs,
        })

    # -------------------------------------------------------------------------
    # EXPORT HELPERS
    # -------------------------------------------------------------------------

    def subfolder(self):
        return 'export'

    @classmethod
    def _generate_invoice_ubl_file(cls, invoice):
        cls.env['account.move.send'].create({'move_ids': [Command.set(invoice.ids)]}).action_send_and_print()

    def _assert_invoice_ubl_file(self, invoice, filename):
        self.assertTrue(invoice.ubl_cii_xml_id)
        self.assert_xml(invoice.ubl_cii_xml_id.raw, filename, subfolder=self.subfolder())

    # -------------------------------------------------------------------------
    # IMPORT HELPERS
    # -------------------------------------------------------------------------

    @classmethod
    def _import_as_attachment_on(cls, file_path=None, attachment=None, journal=None):
        assert file_path or attachment
        assert not file_path or not attachment
        journal = journal or cls.company_data["default_journal_purchase"]
        if file_path:
            attachment = cls._import_as_attachment(file_path)
        return journal._create_document_from_attachment(attachment.id)


class TestUblCiiBECommon(TestUblCiiCommon):

    @classmethod
    def setup_company_data(cls, company_name, chart_template=None, **kwargs):
        kwargs.setdefault('invoice_is_ubl_cii', True)
        results = super().setup_company_data(company_name, chart_template=chart_template, **kwargs)
        company = results['company']
        company.partner_id.write({
            'street': "Chaussée de Namur 40",
            'zip': "1367",
            'city': "Ramillies",
            'vat': 'BE0202239951',
            'company_registry': '0202239951',
            'country_id': cls.env.ref('base.be').id,
            'bank_ids': [Command.create({'acc_number': 'BE15001559627230'})],
        })
        return results

    def subfolder(self):
        return f'{super().subfolder()}/be'


class TestUblBis3Common(TestUblCiiCommon):

    @classmethod
    def _create_partner_be(cls, **kwargs):
        kwargs.setdefault('ubl_cii_format', 'ubl_bis3')
        return super()._create_partner_be(**kwargs)

    @classmethod
    def _create_partner_lu_dig(cls, **kwargs):
        kwargs.setdefault('ubl_cii_format', 'ubl_bis3')
        return super()._create_partner_lu_dig(**kwargs)

    # -------------------------------------------------------------------------
    # EXPORT HELPERS
    # -------------------------------------------------------------------------

    def subfolder(self):
        return super().subfolder().replace('export', 'export/bis3/invoice')
