from odoo.tests import tagged
from .common import TestPeEdiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestSequence(TestPeEdiCommon):

    def test_sequence_prefix_with_numbers(self):
        journal = self.company_data['default_journal_sale'].copy()
        journal.code = "XYZ"
        move = self._create_invoice(name='/', journal_id=journal.id)
        move.action_post()
        # Next invoice is resequenced to use a prefix with numbers in it
        journal.code = "01A"
        move2 = self._create_invoice(name='F F01-00000001', journal_id=journal.id)
        move2.action_post()
        move3 = self._create_invoice(name='/', journal_id=journal.id)
        move3.action_post()
        self.assertEqual(move2.name[:6], move3.name[:6], "The next invoice should use the new prefix")
