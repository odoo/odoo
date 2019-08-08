# -*- coding: utf-8 -*-
from unittest.mock import patch

from odoo.tests import tagged
from odoo.addons.point_of_sale.tests.test_frontend import TestUiBase
from odoo.addons.pos_ipaymu.tests.common import MockResponse, mocked_ipaymu_requests_post


@tagged('post_install', '-at_install')
class TestPosIpaymuFrontend(TestUiBase):

    def setUp(self):
        super().setUp()

        # Create the payment methods
        cash_journal = self.env['account.journal'].create({
            'name': 'CASH',
            'type': 'cash',
            'code': 'CASH',
            'journal_user': True,
            })
        self.ipaymu_config = self.env['pos_ipaymu.configuration'].create({
            'name': 'Ipaymu Test',
            'merchant_api_key': '0oLuh.EV6dF3FZRqn5t8aFDZ2sFoH1'
            })
        ipaymu_journal = self.env['account.journal'].create({
            'name': 'IPaymu',
            'type': 'bank',
            'code': 'IP',
            'journal_user': True,
            'pos_ipaymu_config_id': self.ipaymu_config.id,
            })
        self.pos_config.journal_ids |= ipaymu_journal

    @patch('requests.post', side_effect=mocked_ipaymu_requests_post)
    def test_get_payment_status(self, mock_post):
        MockResponse.reset()
        
        # open a session, the /pos/web controller will redirect to it
        self.pos_config.open_session_cb()

        self.start_tour("/pos/web", 'pos_ipaymu', login="admin")
