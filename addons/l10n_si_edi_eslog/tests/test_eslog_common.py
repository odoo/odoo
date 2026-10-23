from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class TestL10nSiEslogCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('account_edi_ubl_cii.use_new_dict_to_xml_helpers', True)
        cls.env.company.tax_calculation_rounding_method = 'round_globally'
        cls.partner_a.invoice_edi_format = 'eslog'
        #cls.product_a.product_tmpl_id.l10n_hr_kpd_category_id = cls.env['l10n_hr.kpd.category'].search([('name', '=', '01.11.11')])
        #cls.env.user.partner_id.l10n_hr_personal_oib = '01234567896'

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
        create_values['country_id'] = cls.env.ref('base.si').id
        return super()._create_company(**create_values)

    def setup_partner_as_si(self, partner):
        partner.write({
            'street': "Slovenian Street 1",
            'zip': "1234",
            'city': "Slovenian City",
            'vat': 'SI12345679',
            'country_id': self.env.ref('base.si').id,
            'bank_ids': [Command.create({'acc_number': 'SI10000000000000', 'allow_out_payment': True})],
            'email': 'test1@test.test',
            #'invoice_sending_method': 'eslog',
        })

    def setup_partner_as_si_alt(self, partner):
        partner.write({
            'street': "Slovenian Street 2",
            'zip': "5678",
            'city': "Other Slovenian City",
            'vat': 'SI10000003',
            'country_id': self.env.ref('base.si').id,
            'bank_ids': [Command.create({'acc_number': 'SI20000000000000', 'allow_out_payment': True})],
            'email': 'test3@test.test',
            #'invoice_sending_method': 'eslog',
        })
