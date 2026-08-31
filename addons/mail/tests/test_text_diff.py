# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.tests.common import BaseCase, tagged
from odoo.addons.mail.tools.text import text_diff_summary


@tagged('at_install')
class TestTextDiff(BaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_text = re.sub(r'\s+', ' ', '''
            ’Twas brillig, and the slithy toves
            Did gyre and gimble in the wabe;
            All mimsy were the borogoves,
            And the mome raths outgrabe.
        ''').strip()

    def test_unchanged(self):
        """Summaries should be '...' when there is no change"""
        diff_1, diff_2 = text_diff_summary(self.base_text, self.base_text, 5)
        rev_diff_1, rev_diff_2 = text_diff_summary(self.base_text, self.base_text, 5)
        self.assertEqual(diff_1, rev_diff_2, "Direction should not matter")
        self.assertEqual(diff_2, rev_diff_1, "Direction should not matter")
        self.assertEqual(diff_1, '...')
        self.assertEqual(diff_2, '...')

    def test_middle(self):
        """Summaries should have ellipsis around a change in the middle"""
        alt_text = self.base_text.replace('slithy', 'slictuous')
        diff_1, diff_2 = text_diff_summary(self.base_text, alt_text, 5)
        rev_diff_1, rev_diff_2 = text_diff_summary(alt_text, self.base_text, 5)
        self.assertEqual(diff_1, rev_diff_2, "Direction should not matter")
        self.assertEqual(diff_2, rev_diff_1, "Direction should not matter")
        self.assertEqual(diff_1, '...e slithy tove...')
        self.assertEqual(diff_2, '...e slictuous tove...')

    def test_near_border(self):
        """Summaries should not have ellipsis before start nor after end"""
        alt_text = self.base_text.replace('’Twas', '’Twere').replace('outgrabe', 'outgave')
        diff_1, diff_2 = text_diff_summary(self.base_text, alt_text, 5)
        rev_diff_1, rev_diff_2 = text_diff_summary(alt_text, self.base_text, 5)
        self.assertEqual(diff_1, rev_diff_2, "Direction should not matter")
        self.assertEqual(diff_2, rev_diff_1, "Direction should not matter")
        self.assertEqual(diff_1, '’Twas bril... outgrabe.')
        self.assertEqual(diff_2, '’Twere bril... outgave.')

    def test_first_last(self):
        """Summaries should show difference on first and last character"""
        alt_text = self.base_text.replace('’Twas', 'It was').replace('outgrabe.', 'outgrabe!')
        diff_1, diff_2 = text_diff_summary(self.base_text, alt_text, 5)
        rev_diff_1, rev_diff_2 = text_diff_summary(alt_text, self.base_text, 5)
        self.assertEqual(diff_1, rev_diff_2, "Direction should not matter")
        self.assertEqual(diff_2, rev_diff_1, "Direction should not matter")
        self.assertEqual(diff_1, '’Twas b...grabe.')
        self.assertEqual(diff_2, 'It was b...grabe!')

    def test_symmetry(self):
        """Summaries should not be asymmetrical even when the change paths in both directions are different"""
        alt_text = self.base_text.replace('mome raths', 'verchons')
        diff_1, diff_2 = text_diff_summary(self.base_text, alt_text, 5)
        rev_diff_1, rev_diff_2 = text_diff_summary(alt_text, self.base_text, 5)
        self.assertEqual(diff_1, rev_diff_2, "Direction should not matter")
        self.assertEqual(diff_2, rev_diff_1, "Direction should not matter")
        self.assertEqual(diff_1, '... the mome raths out...')
        self.assertEqual(diff_2, '... the verchons out...')
