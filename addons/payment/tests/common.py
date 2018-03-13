# -*- coding: utf-8 -*-

from odoo.tests import common


class PaymentAcquirerCommon(common.TransactionCase):

    def setUp(self):
        super(PaymentAcquirerCommon, self).setUp()

        self.currency_euro = self.env['res.currency'].search([('name', '=', 'EUR')], limit=1)
        self.country_belgium = self.env['res.country'].search([('code', 'like', 'BE')], limit=1)
        self.country_france = self.env['res.country'].search([('code', 'like', 'FR')], limit=1)

        # dict partner values
        self.buyer_values = {
            'partner_name': 'Norbert Buyer',
            'partner_lang': 'en_US',
            'partner_email': 'norbert.buyer@example.com',
            'partner_address': 'Huge Street 2/543',
            'partner_phone': '0032 12 34 56 78',
            'partner_city': 'Sin City',
            'partner_zip': '1000',
            'partner_country': self.env['res.country'].browse(self.country_belgium.id),
            'partner_country_id': self.country_belgium.id,
            'partner_country_name': 'Belgium',
            'billing_partner_name': 'Norbert Buyer',
            'billing_partner_commercial_company_name': 'Big Company',
            'billing_partner_lang': 'en_US',
            'billing_partner_email': 'norbert.buyer@example.com',
            'billing_partner_address': 'Huge Street 2/543',
            'billing_partner_phone': '0032 12 34 56 78',
            'billing_partner_city': 'Sin City',
            'billing_partner_zip': '1000',
            'billing_partner_country': self.env['res.country'].browse(self.country_belgium.id),
            'billing_partner_country_id': self.country_belgium.id,
            'billing_partner_country_name': 'Belgium',
        }

        # test partner
        self.buyer = self.env['res.partner'].create({
            'name': 'Norbert Buyer',
            'lang': 'en_US',
            'email': 'norbert.buyer@example.com',
            'street': 'Huge Street',
            'street2': '2/543',
            'phone': '0032 12 34 56 78',
            'city': 'Sin City',
            'zip': '1000',
            'country_id': self.country_belgium.id})
        self.buyer_id = self.buyer.id
