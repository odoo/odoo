from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged

from .common import TestPosTbaiCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPosEdi(TestPosTbaiCommon):

    def test_post_pos_order(self):
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        pos_order = self.PosOrder.create({
            'session_id': current_session.id,
            'partner_id': self.partner_b.id,
            'lines': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 100,
                    'qty': 1,
                    'tax_ids': self._get_tax_by_xml_id('s_iva21b').ids,
                }),
            ],
            'amount_tax': 21.0,
            'amount_total': 121.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
        })

        context_make_payment = {
            'active_ids': pos_order.ids,
            'active_id': pos_order.id,
        }
        pos_make_payment = self.PosMakePayment.with_context(context_make_payment).create({
            'amount': 121,
        })

        with patch(
            'odoo.addons.l10n_es_edi_tbai.models.l10n_es_edi_tbai_document.requests.Session.request',
            return_value=self.mock_response_post_invoice_success,
        ):
            pos_make_payment.with_context(context_make_payment).check()

        self.assertEqual(pos_order.state, 'paid')
        self.assertEqual(pos_order.l10n_es_tbai_state, 'sent')
