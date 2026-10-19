# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_get_siren_and_siret_country(self):
        for country_code in ('FR', 'BE', False):
            for registry in ('334175221', '33417522100010', False):
                with self.subTest(country_code=country_code, registry=registry):
                    partner = self.env['res.partner'].new({
                        'country_id': self.env.ref(f'base.{country_code.lower()}').id if country_code else False,
                        'company_registry': registry,
                        'vat': 'FR23334175221',
                    })
                    self.assertEqual(partner._l10n_fr_get_siren(), '334175221' if country_code == 'FR' else False)
                    self.assertEqual(
                        partner._l10n_fr_get_siret(),
                        '33417522100010' if country_code == 'FR' and registry == '33417522100010' else False,
                    )

    def test_get_siren_from_vat(self):
        for vat, expected_siren in (
            ('FR23334175221', '334175221'),
            ('fr 23 334 175 221', '334175221'),
            ('BE23334175221', None),
        ):
            with self.subTest(vat=vat):
                partner = self.env['res.partner'].new({'vat': vat})
                self.assertEqual(partner._l10n_fr_get_siren_from_vat(), expected_siren)
