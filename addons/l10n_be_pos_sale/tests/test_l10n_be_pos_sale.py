# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.test_common import TestPointOfSaleDataHttpCommon
from odoo import Command

@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestPoSSaleL10NBe(TestPointOfSaleDataHttpCommon):

    @classmethod
    @TestPointOfSaleDataHttpCommon.setup_country('be')
    def setUpClass(self):
        super().setUpClass()
        self.env.user.group_ids += self.env.ref('sales_team.group_sale_salesman')

    def test_settle_order_is_invoice(self):
        intracom_fpos = self.env["account.chart.template"].with_company(self.env.user.company_id).ref("fiscal_position_template_3", False)
        intracom_tax = self.env['account.tax'].create({
            'name': 'test_intracom_taxes_computation_0_1',
            'amount_type': 'percent',
            'amount': 21,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': 100.0}),
                (0, 0, {'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        })

        intracom_fpos.tax_ids.tax_dest_id = intracom_tax
        self.product_awesome_item.write({
            'list_price': 10,
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_awesome_item.product_variant_id.id,
                'product_uom_qty': 10,
                'price_unit': 10,
                'tax_ids': intracom_tax,
            })],
        })

        sale_order.action_confirm()
        sale_order2 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_awesome_item.product_variant_id.id,
                'product_uom_qty': 20,
                'price_unit': 20,
                'tax_ids': False,
            })],
        })
        sale_order2.action_confirm()
        self.start_pos_tour('PosSettleOrderIsInvoice', login="accountman")


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestPoSSaleL10NBeNormalCompany(TestPointOfSaleDataHttpCommon):
    def test_settle_order_can_invoice(self):
        """This test makes sure that you can invoice a settled order when l10n_be is installed"""
        self.env.user.group_ids += self.env.ref('sales_team.group_sale_salesman')
        self.env['sale.order'].create({
            'partner_id': self.partner_one.id,
            'order_line': [Command.create({
                'product_id': self.product_awesome_item.product_variant_id.id,
                'product_uom_qty': 10,
                'price_unit': 10,
            })],
        })
        self.start_pos_tour('PosSettleOrderTryInvoice', login="accountman")
