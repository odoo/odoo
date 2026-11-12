# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date

from odoo.addons.l10n_np.tools.bikram_samwat import convert_ad_to_bs
from odoo.tests import BaseCase, tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestBikramSamwat(BaseCase):

    def test_convert_ad_to_bs(self):
        self.assertEqual(convert_ad_to_bs(date(2026, 4, 14)), (2083, 1, 1))   # Nepali New Year 2083
        self.assertEqual(convert_ad_to_bs(date(2026, 11, 6)), (2083, 7, 20))  # Kartik 20, 2083
