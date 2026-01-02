from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nHrEdiCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        cls.env.company.tax_calculation_rounding_method = 'round_globally'
        cls.partner_a.invoice_edi_format = 'ubl_hr'
        cls.product_a.product_tmpl_id.l10n_hr_kpd_category_id = cls.env['l10n_hr.kpd.category'].search([('name', '=', '01.11.11')])
        cls.env.user.partner_id.l10n_hr_personal_oib = '01234567896'

        cls.pay_term_epd_mixed = cls.env['account.payment.term'].create({
            'name': "2/7 Net 30",
            'note': "Payment terms: 30 Days, 2% Early Payment Discount under 7 days",
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 7,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({'value': 'percent', 'value_amount': 100.0, 'nb_days': 30})],
        })

    @classmethod
    def _create_company(cls, **create_values):
        # EXTENDS 'account'
        create_values['currency_id'] = cls.env.ref('base.EUR').id
        create_values['country_id'] = cls.env.ref('base.hr').id
        return super()._create_company(**create_values)

    def setup_partner_as_hr(self, partner):
        partner.write({
            'street': "Croatian Street 1",
            'zip': "1234",
            'city': "Croatian City",
            'vat': 'HR68139364755',
            'l10n_hr_personal_oib': '68139364755',
            'country_id': self.env.ref('base.hr').id,
            'bank_ids': [Command.create({'acc_number': 'HR10000000000000'})],
            'email': 'test1@test.test',
            'invoice_sending_method': 'mojeracun',
        })

    def setup_partner_as_hr_alt(self, partner):
        partner.write({
            'street': "Croatian Street 2",
            'zip': "5678",
            'city': "Other Croatian City",
            'vat': 'HR08971065561',
            'l10n_hr_personal_oib': '08971065561',
            'country_id': self.env.ref('base.hr').id,
            'bank_ids': [Command.create({'acc_number': 'HR20000000000000'})],
            'email': 'test3@test.test',
            'invoice_sending_method': 'mojeracun',
        })

    def setup_partner_as_mirror(self, partner):
        partner.write({
            'street': "Looking Glass Street 1",
            'zip': "5252",
            'city': "Other Croatian City",
            'vat': 'BE0477472701',
            'l10n_hr_personal_oib': '00000000000',
            'country_id': self.env.ref('base.hr').id,
            'bank_ids': [Command.create({'acc_number': 'HR30000000000000'})],
            'email': 'test-mer-mirror@test.test',
            'invoice_sending_method': 'mojeracun',
        })
