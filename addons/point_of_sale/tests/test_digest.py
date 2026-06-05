# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.point_of_sale.tests.common import CommonPosTest
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import mute_logger
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountDigest(CommonPosTest):

    @classmethod
    @mute_logger('odoo.models.unlink')
    def setUpClass(cls):
        super().setUpClass()
        context = {
            'start_datetime': datetime.now() - relativedelta(days=1),
            'end_datetime': datetime.now() + relativedelta(days=1),
        }

        cls.digest = cls.env['digest.digest'].with_context(context).create([{
            'name': 'Digest 1',
            'company_id': cls.env.company.id,
            'kpi_mail_message_total': True,
            'kpi_res_users_connected': True,
            'periodicity': 'daily',
        }])

    def test_kpi_invoiced_pos_orders_counted(self):
        order_data = {
            'line_data': [
                {'product_id': self.ten_dollars_with_10_incl.product_variant_id.id},
            ],
            'payment_data': [
                {'payment_method_id': self.bank_payment_method.id, 'amount': 10},
            ],
        }

        self.pos_config_usd.open_ui()
        current_session = self.pos_config_usd.current_session_id

        self.create_backend_pos_order({**order_data, 'order_data': {'to_invoice': False, 'partner_id': False}})
        self.create_backend_pos_order({**order_data, 'order_data': {'to_invoice': True, 'partner_id': self.partner.id}})
        current_session.close_session_from_ui()

        self.assertEqual(self.digest.kpi_pos_total_value, 20.0)
