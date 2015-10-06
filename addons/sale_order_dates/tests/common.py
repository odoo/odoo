# -*- coding: utf-8 -*-
from openerp.tests import common


class TestSaleOrderDatesCommon(common.TransactionCase):

    def setUp(self):
        super(TestSaleOrderDatesCommon, self).setUp()

        # Usefull object
        self.sale_order = self.env.ref('sale.sale_order_6')
