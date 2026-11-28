# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
import uuid
from unittest.mock import patch

from odoo import Command
from odoo.tests import tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@tagged('post_install', '-at_install')
class TestMercadoPagoWebhook(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mp_terminal_1, cls.mp_terminal_2 = cls.env['pos.payment.method'].create([{
            'name': name,
            'journal_id': cls.bank_journal.id,
            'use_payment_terminal': 'mercado_pago',
            'mp_webhook_secret_key': 'test-secret',
        } for name in ('MP 1', 'MP 2')])
        cls.main_pos_config.write({
            'payment_method_ids': [Command.link(cls.mp_terminal_1.id), Command.link(cls.mp_terminal_2.id)],
        })
        cls.main_pos_config.open_ui()
        cls.session = cls.main_pos_config.current_session_id
        cls.session.set_opening_control(0, None)

    def _post_webhook(self, payment_method, order_uuid, valid_signature=True):
        data = {
            'id': 'mp-event-1',
            'additional_info': {'external_reference': f'{self.session.id}_{payment_method.id}_{order_uuid}'},
        }
        with patch('odoo.addons.pos_mercado_pago.controllers.main.hmac.compare_digest', return_value=valid_signature):
            return self.url_open('/pos_mercado_pago/notification', data=json.dumps(data), headers={
                'Content-Type': 'application/json',
                'X-Request-Id': 'req-1',
                'X-Signature': 'ts=1700000000,v1=0123456789abcdef',
            })

    def test_webhook_notifies_its_terminal_and_order(self):
        """ Every device of the config receives the message: it must say which
        terminal and order it is about, so the other devices keep waiting. """
        order_uuid_1, order_uuid_2 = str(uuid.uuid4()), str(uuid.uuid4())
        with patch.object(self.registry['pos.config'], '_notify', autospec=True) as notify:
            self.assertEqual(self._post_webhook(self.mp_terminal_1, order_uuid_1).status_code, 200)
            self.assertEqual(self._post_webhook(self.mp_terminal_2, order_uuid_2).status_code, 200)
            # wrong signature: no notification at all
            with mute_logger('odoo.addons.pos_mercado_pago.controllers.main'):
                self.assertEqual(
                    self._post_webhook(self.mp_terminal_1, order_uuid_1, valid_signature=False).status_code, 401,
                )

        self.assertEqual([call.args[1:] for call in notify.call_args_list], [
            ('MERCADO_PAGO_LATEST_MESSAGE', {
                'config_id': self.main_pos_config.id,
                'payment_method_id': self.mp_terminal_1.id,
                'pos_order_uuid': order_uuid_1,
            }),
            ('MERCADO_PAGO_LATEST_MESSAGE', {
                'config_id': self.main_pos_config.id,
                'payment_method_id': self.mp_terminal_2.id,
                'pos_order_uuid': order_uuid_2,
            }),
        ])
