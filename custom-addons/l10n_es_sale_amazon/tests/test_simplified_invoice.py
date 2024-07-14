# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.sale_amazon.tests.common import TestAmazonCommon, OPERATIONS_RESPONSES_MAP
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAmazonES(TestAmazonCommon, AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref='es_full'):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.company_data['company'].write({
            'country_id': cls.env.ref('base.es').id,
            'street': 'C. de Embajadores, 68-116',
            'state_id': cls.env.ref('base.state_es_m').id,
            'city': 'Madrid',
            'zip': '12345',
            'vat': 'ES59962470K',
        })

    def test_amazon_invoice_simplified(self):
        # Create an amazon sale.order from the mocked amazon account that is set in sale_amazon/tests/common.py.
        with patch(
            'odoo.addons.sale_amazon.utils.make_sp_api_request',
            new=lambda _account, operation_, **_kwargs: OPERATIONS_RESPONSES_MAP[operation_]
        ):
            self.account._sync_orders(auto_commit=False)
            sale_order = self.env['sale.order'].search([('amazon_order_ref', '=', '123456789')])

        # Validate the picking so we can invoice the sale order. After having filled the required fields
        # to validate the  `_check_carrier_details_compliance` constrain introduced in sale_amazon.
        picking = sale_order.picking_ids
        picking.write({
            'carrier_id': self.carrier,
            'carrier_tracking_ref': self.tracking_ref,
        })
        picking.button_validate()

        invoice = sale_order._create_invoices()

        self.assertTrue(invoice.l10n_es_is_simplified)
