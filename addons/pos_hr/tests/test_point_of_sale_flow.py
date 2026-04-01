# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

import odoo
from odoo import Command
from odoo.addons.point_of_sale.tests.common import CommonPosTest, TestPoSCommon
from odoo.exceptions import UserError


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(CommonPosTest):
    def test_pos_hr_session_name_gap(self):
        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id
        session.set_opening_control(0, None)
        current_session_name = session.name
        session.action_pos_session_closing_control()

        self.pos_config_usd.open_ui()
        session = self.pos_config_usd.current_session_id

        def _message_post_patch(*_args, **_kwargs):
            raise UserError('Test Error')

        with patch.object(self.env.registry.models['pos.session'], "message_post", _message_post_patch):
            with self.assertRaises(UserError):
                session.set_opening_control(0, None)

        session.set_opening_control(0, None)
        self.assertEqual(int(session.name.split('/')[1]), int(current_session_name.split('/')[1]) + 1)


@odoo.tests.tagged('post_install', '-at_install')
class TestPosHrBatchWrite(TestPoSCommon):

    def test_batch_write_multi_company_singleton(self):
        company_b = self.setup_other_company(name='Company B')

        payment_method_b = self.env['pos.payment.method'].create({
            'name': 'Cash B',
            'receivable_account_id': company_b['default_account_receivable'].id,
            'journal_id': company_b['default_journal_cash'].id,
            'company_id': company_b['company'].id,
        })
        pos_config_b = self.env['pos.config'].create({
            'name': 'Config B',
            'company_id': company_b['company'].id,
            'journal_id': company_b['default_journal_sale'].id,
            'invoice_journal_id': company_b['default_journal_sale'].id,
            'payment_method_ids': [Command.set([payment_method_b.id])],
        })
        configs = self.basic_config | pos_config_b
        configs.write({'cash_rounding': False})

        self.assertFalse(any(configs.mapped('cash_rounding')))
