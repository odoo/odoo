# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_tw_edi_ecpay.tests.test_edi import L10nTWITestEdi
from odoo.tests import tagged


CALL_API_METHOD = 'odoo.addons.l10n_tw_edi_ecpay.utils.EcPayAPI.call_ecpay_api'


@tagged('post_install_l10n', 'post_install', '-at_install')
class L10nTWITestEdiSaleOrder(L10nTWITestEdi):
    def test_01_so_data_forward_to_invoice(self):
        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'l10n_tw_edi_is_print': True,
            'l10n_tw_edi_love_code': "ABC123",
            'l10n_tw_edi_carrier_type': "2",
            'l10n_tw_edi_carrier_number': "12345678",
            'l10n_tw_edi_carrier_number_2': "87654321",
        })

        self.env['sale.order.line'].create({
            'name': self.product_a.name,
            'product_id': self.product_a.id,
            'product_uom_qty': 1,
            'order_id': so.id,
        })

        so.action_confirm()
        invoice = self.env['account.move'].create(so._prepare_invoice())

        self.assertRecordValues(invoice, [{
            'l10n_tw_edi_is_print': so.l10n_tw_edi_is_print,
            'l10n_tw_edi_love_code': so.l10n_tw_edi_love_code,
            'l10n_tw_edi_carrier_type': so.l10n_tw_edi_carrier_type,
            'l10n_tw_edi_carrier_number': so.l10n_tw_edi_carrier_number,
            'l10n_tw_edi_carrier_number_2': so.l10n_tw_edi_carrier_number_2,
        }])
