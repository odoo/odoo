# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class PaymentAcquirerCommon(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_euro = cls.env.ref('base.EUR')
        cls.country_belgium = cls.env.ref('base.be')
        cls.country_france = cls.env.ref('base.fr')

        # dict partner values
        cls.buyer_values = {
            'partner_name': 'Norbert Buyer',
            'partner_lang': 'en_US',
            'partner_email': 'norbert.buyer@example.com',
            'partner_address': 'Huge Street 2/543',
            'partner_phone': '0032 12 34 56 78',
            'partner_city': 'Sin City',
            'partner_zip': '1000',
            'partner_country': cls.country_belgium,
            'partner_country_id': cls.country_belgium.id,
            'partner_country_name': 'Belgium',
            'billing_partner_name': 'Norbert Buyer',
            'billing_partner_commercial_company_name': 'Big Company',
            'billing_partner_lang': 'en_US',
            'billing_partner_email': 'norbert.buyer@example.com',
            'billing_partner_address': 'Huge Street 2/543',
            'billing_partner_phone': '0032 12 34 56 78',
            'billing_partner_city': 'Sin City',
            'billing_partner_zip': '1000',
            'billing_partner_country': cls.country_belgium,
            'billing_partner_country_id': cls.country_belgium.id,
            'billing_partner_country_name': 'Belgium',
        }

        # test partner
        cls.buyer = cls.env['res.partner'].create({
            'name': 'Norbert Buyer',
            'lang': 'en_US',
            'email': 'norbert.buyer@example.com',
            'street': 'Huge Street',
            'street2': '2/543',
            'phone': '0032 12 34 56 78',
            'city': 'Sin City',
            'zip': '1000',
            'country_id': cls.country_belgium.id})
        cls.buyer_id = cls.buyer.id
