from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_latam_is_company(self):
        latam_fake_country = self.env['res.country'].create({
            'name': "LATAM fake country",
            'code': 'YY',
        })
        it_vat = self.env.ref('l10n_latam_base.it_vat')  # VAT
        it_pass = self.env.ref('l10n_latam_base.it_pass')  # passport
        (it_vat + it_pass).write({'country_id': latam_fake_country.id})
        with patch('odoo.addons.l10n_latam_base.models.res_company.ResCompany._get_l10n_latam_base_country_codes', return_value=['YY']):
            latam_company, latam_person, foreign_company, foreign_person = self.env['res.partner'].create([
                {
                    'name': 'LATAM Company',
                    'l10n_latam_identification_type_id': it_vat.id,
                    'country_id': latam_fake_country.id,
                    'vat': '12345',
                },
                {
                    'name': 'LATAM Person',
                    'l10n_latam_identification_type_id': it_pass.id,
                    'country_id': latam_fake_country.id,
                    'vat': '12345',
                },
                {
                    'name': 'Foreign Company',
                    'l10n_latam_identification_type_id': False,
                    'vat': '12345',
                },
                {
                    'name': 'Foreign Person',
                    'l10n_latam_identification_type_id': False,
                    'vat': False,
                },
            ])
            self.assertTrue(latam_company.is_company)
            self.assertFalse(latam_person.is_company)
            self.assertTrue(foreign_company.is_company)
            self.assertFalse(foreign_person.is_company)
