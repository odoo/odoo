from odoo.addons.l10n_in_pos.tests.common import TestInPosBase
from odoo.tests import tagged
from datetime import date

TEST_DATE = date(2023, 5, 20)


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPOSGstrSection(TestInPosBase):

    def test_b2cs_gstr_section_with_pos_order(self):
        with self.with_pos_session() as session:
            self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product_a, 2.0),  # 2 units of product A
                    (self.product_b, 2.0),  # 2 units of product B
                ],
                'payments': [(self.bank_pm1, 630.0)],
            })
            session.action_pos_session_closing_control()
            pos_entry_lines = session.move_id.line_ids
            for line in pos_entry_lines.filtered(lambda l: l.display_type in ('product, tax')):
                self.assertEqual(line.l10n_in_gstr_section, 'sale_b2cs')

    def test_nil_rated_gstr_section_with_pos_order(self):
        with self.with_pos_session() as session:
            self._create_order({
                'pos_order_lines_ui_args': [
                    (self.product_c, 3.0),  # 3 units of product C
                ],
                'payments': [(self.bank_pm1, 900.0)],
                'customer': self.partner_a,
            })
            session.action_pos_session_closing_control()
            pos_entry_lines = session.move_id.line_ids
            for line in pos_entry_lines.filtered(lambda l: l.display_type in ('product, tax')):
                self.assertEqual(line.l10n_in_gstr_section, 'sale_nil_rated')
