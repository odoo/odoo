# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPAddressFormat(TransactionCase):
    def test_address_reads_from_the_largest_area_down(self):
        partner = self.env['res.partner'].create({
            'name': 'JP Trading',
            'country_id': self.env.ref('base.jp').id,
            'zip': '100-0005',
            'state_id': self.env.ref('base.state_jp_jp-13').id,
            'city': '千代田区',
            'street': '丸の内1-1-1',
            'street2': '5F',
        })
        self.assertEqual(
            partner._display_address(without_name=True),
            '100-0005\nJapan 東京都 千代田区\n丸の内1-1-1\n5F',
        )
