# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase, tagged


@tagged('post_install_l10n', '-at_install', 'post_install')
class TestJPAddressFormat(TransactionCase):
    def test_jp_country_address_format(self):
        jp_country = self.env.ref('base.jp')
        self.assertEqual(
            jp_country.mapped('address_format')[0],
            '%(zip)s\n%(state_name)s %(city)s\n%(street)s\n%(street2)s\n%(country_name)s',
        )
