# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nHuAddress(TransactionCase):

    def test_address_format(self):
        partner = self.env['res.partner'].create({
            'name': 'Teszt Kft.',
            'street': 'Fo utca 1.',
            'street2': 'II. emelet 3.',
            'zip': '1011',
            'city': 'Budapest',
            'country_id': self.env.ref('base.hu').id,
        })
        self.assertEqual(partner._display_address(without_name=True), "1011 Budapest, Fo utca 1.\nII. emelet 3.\nHungary")

    def test_city_fills_zip(self):
        self.env.company.country_id = self.env.ref('base.hu')
        city = self.env.ref('l10n_hu.city_hu_2660_1')
        with Form(self.env['res.partner']) as partner_form:
            partner_form.name = 'Teszt Kft.'
            partner_form.country_id = self.env.ref('base.hu')
            partner_form.city_id = city
        partner = partner_form.save()
        self.assertRecordValues(partner, [{'city': 'Balassagyarmat', 'zip': '2660'}])
