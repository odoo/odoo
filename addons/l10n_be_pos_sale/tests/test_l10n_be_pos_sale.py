# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo

from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command

@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestPoSSaleL10NBe(TestPointOfSaleHttpCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='be_comp'):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def test_settle_order_is_invoice(self):
        #Change company country to Belgium
        self.env.user.company_id.country_id = self.env.ref('base.be')

        intracom_fpos = self.env["account.chart.template"].with_company(
            self.env.user.company_id).ref("fiscal_position_template_3", False)

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

        self.product_a = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
        })

        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 10,
                'tax_id': intracom_tax,
            })],
        })

        sale_order.action_confirm()
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderIsInvoice', login="accountman")


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestPoSSaleL10NBeNormalCompany(TestPointOfSaleHttpCommon):
    def test_settle_order_can_invoice(self):
        """This test makes sure that you can invoice a settled order when l10n_be is installed"""
        self.product_a = self.env['product.product'].create({
            'name': 'Product A',
            'type': 'product',
            'list_price': 10,
            'taxes_id': False,
            'available_in_pos': True,
        })

        self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 10,
                'product_uom': self.product_a.uom_id.id,
                'price_unit': 10,
            })],
        })
        self.main_pos_config.open_ui()
        self.start_tour("/pos/ui?config_id=%d" % self.main_pos_config.id, 'PosSettleOrderTryInvoice', login="accountman")
