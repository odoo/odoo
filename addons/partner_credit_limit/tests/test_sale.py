# See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class TestSaleTestCase(common.TransactionCase):

    def setup(self):
        super(TestSaleTestCase, self).setup()

    def test_sale(self):
        self.respartner_obj = self.env['res.partner']
        self.partner = self.respartner_obj.create({
            'name': 'Partner Name',
            'over_credit': True,
        })
        self.env['sale.order'].create({
            'partner_id': self.partner.id,
        }).action_confirm()
