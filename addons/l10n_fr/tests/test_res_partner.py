# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_get_siren_from_vat(self):
        for vat, expected_siren in (
            ('FR23334175221', '334175221'),
            ('fr 23 334 175 221', '334175221'),
            ('FRK7399859412', '399859412'),
            ('FR4Z123456782', '123456782'),
            ('BE23334175221', None),
        ):
            with self.subTest(vat=vat):
                partner = self.env['res.partner'].new({'vat': vat})
                self.assertEqual(partner._l10n_fr_get_siren_from_vat(), expected_siren)

    def test_compute_company_registry_from_vat(self):
        for country, vat, expected_siren in (
            ('fr', 'FR23334175221', '334175221'),
            ('be', 'FR23334175221', '334175221'),
            ('fr', 'fr 23 334 175 221', '334175221'),
            ('fr', 'FRK7399859412', '399859412'),
        ):
            with self.subTest(country=country, vat=vat):
                partner = self.env['res.partner'].create({
                    'name': 'Partner with French VAT',
                    'country_id': self.env.ref(f'base.{country}').id,
                    'vat': vat,
                })
                self.assertEqual(partner.company_registry, expected_siren)
                partner.vat = 'FR35562153452'
                self.assertEqual(partner.company_registry, expected_siren, "The company_registry shouldn't change once it has been set")

        partner = self.env['res.partner'].create({'name': 'Partner without VAT'})
        self.assertFalse(partner.company_registry)
        partner.vat = 'FR23334175221'
        self.assertEqual(partner.company_registry, '334175221')

    def test_compute_company_registry_preserves_explicit_identifiers(self):
        for field, values in (
            ('company_registry', ('968515759', '96851575905877', '.', '/')),
            ('siret', ('96851575905877', '.', '/')),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    partner = self.env['res.partner'].create({
                        'name': 'Partner with an explicit identifier',
                        'country_id': self.env.ref('base.fr').id,
                        'vat': 'FR23334175221',
                        field: value,
                    })
                    self.assertEqual(partner[field], value)
                    if field == 'siret':
                        self.assertFalse(partner.company_registry)
                    partner.vat = 'FR35562153452'
                    self.assertEqual(partner[field], value)
                    if field == 'siret':
                        self.assertFalse(partner.company_registry)
