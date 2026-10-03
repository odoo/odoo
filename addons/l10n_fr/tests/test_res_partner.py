# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestResPartner(TransactionCase):

    def test_get_siren_from_vat(self):
        for vat, expected_siren in (
            ('FR23334175221', '334175221'),
            ('fr 23 334 175 221', '334175221'),
            ('BE23334175221', False),
        ):
            with self.subTest(vat=vat):
                partner = self.env['res.partner'].new({'vat': vat})
                self.assertEqual(partner._l10n_fr_get_siren_from_vat(), expected_siren)
