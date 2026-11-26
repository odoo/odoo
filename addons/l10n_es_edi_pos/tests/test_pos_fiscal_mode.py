# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests import tagged

from .common import TestL10nEsEdiPosCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nEsEdiPosFiscalMode(TestL10nEsEdiPosCommon):

    def _get_fiscal_mode(self, available_modes):
        with patch.object(
            self.env.registry['res.company'],
            '_l10n_es_pos_get_available_fiscal_modes',
            lambda company: set(available_modes),
        ):
            return self.company._l10n_es_pos_get_fiscal_mode()

    def test_no_fiscal_mode(self):
        self.assertFalse(self._get_fiscal_mode([]))

    def test_single_fiscal_mode(self):
        for mode in ('tbai', 'sii', 'verifactu'):
            with self.subTest(mode=mode):
                self.assertEqual(self._get_fiscal_mode([mode]), mode)

    def test_fiscal_mode_priority(self):
        """ The result follows POS_FISCAL_MODE_PRIORITY, whatever order the modes were added in. """
        cases = [
            (['sii', 'tbai'], 'tbai'),
            (['verifactu', 'tbai'], 'tbai'),
            (['verifactu', 'sii'], 'sii'),
            (['verifactu', 'sii', 'tbai'], 'tbai'),
        ]
        for available_modes, expected_mode in cases:
            with self.subTest(available_modes=available_modes):
                self.assertEqual(self._get_fiscal_mode(available_modes), expected_mode)

    def test_pos_edi_mode(self):
        """ The VAT books list the POS orders one by one for TicketBAI and Veri*Factu only:
        with SII, they are reported through the F4 session closing entry. """
        cases = [('tbai', 'tbai'), ('verifactu', 'verifactu'), ('sii', False), (False, False)]
        for mode, expected_edi_mode in cases:
            with self.subTest(mode=mode), self._patch_fiscal_mode(mode):
                self.assertEqual(self.company._l10n_es_get_pos_edi_mode(), expected_edi_mode)
