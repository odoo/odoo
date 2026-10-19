# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_get_siren_and_siret_country(self):
        partner = self.env['res.partner'].new({
            'country_id': self.env.ref('base.fr').id,
            'company_registry': '33417522100010',
            'vat': 'FR23334175221',
        })
        self.assertEqual(partner._l10n_fr_get_siren(), '334175221')
        self.assertEqual(partner._l10n_fr_get_siret(), '33417522100010')

        partner.write({
          'vat': "BE23334175221",
          'country_id': self.env.ref('base.be').id
        })
        self.assertFalse(partner._l10n_fr_get_siren())
        self.assertFalse(partner._l10n_fr_get_siret())

    def test_get_siren_from_vat(self):
        for vat, expected_siren in (
            ('FR23334175221', '334175221'),
            ('fr 23 334 175 221', '334175221'),
            ('BE23334175221', None),
        ):
            with self.subTest(vat=vat):
                partner = self.env['res.partner'].new({'vat': vat})
                self.assertEqual(partner._l10n_fr_get_siren_from_vat(), expected_siren)
