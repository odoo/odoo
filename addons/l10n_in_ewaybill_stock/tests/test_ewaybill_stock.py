from freezegun import freeze_time

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import _
from odoo.fields import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestStockEwaybill(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass(chart_template_ref='in')
        cls.env.company.write({
            'state_id': cls.env.ref('base.state_in_gj').id,
            'zip': '380004'
        })
        cls.env.user.groups_id += cls.env.ref('stock.group_stock_manager')
        cls.sgst_sale_5 = cls.env["account.chart.template"].ref("sgst_sale_5")
        cls.product_a.write({
            "l10n_in_hsn_code": "01111",
            'taxes_id': [Command.set(cls.sgst_sale_5.ids)],
            'standard_price': 500.00
        })
        cls.partner_a.write({
            'vat': '27DJMPM8965E1ZE',
            'l10n_in_gst_treatment': 'regular',
            'state_id': cls.env.ref("base.state_in_mh").id,
            'country_id': cls.env.ref('base.in').id,
            'zip': '431122'
        })

    @freeze_time('2024-04-26')
    def test_ewaybill_stock(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)])
        delivery_picking = self.env['stock.picking'].create({
            'partner_id': self.partner_a.id,
            'picking_type_id': warehouse.out_type_id.id,
            'move_ids': [Command.create({
                'name': self.product_a.name,
                'product_id': self.product_a.id,
                'product_uom_qty': 5,
                'quantity': 5,
                'location_id': self.env.ref('stock.stock_location_customers').id,
                'location_dest_id': warehouse.lot_stock_id.id,
            })]
        })
        delivery_picking.button_validate()
        ewaybill = self.env['l10n.in.ewaybill'].create({
            'picking_id': delivery_picking.id,
            'mode': False,
            'type_id': self.env.ref('l10n_in_ewaybill_stock.type_delivery_challan_sub_line_sales').id,
        })
        self.assertRecordValues(ewaybill, [{
            'state': 'pending',
            'display_name': _('Pending'),
            'fiscal_position_id': self.env['account.fiscal.position'],
        }])
        ewaybill.fiscal_position_id = self.env['account.chart.template'].ref('fiscal_position_in_inter_state')
        self.assertEqual(ewaybill.move_ids[0].ewaybill_tax_ids, self.env['account.chart.template'].ref('igst_sale_5'))
        expected_json = {
            'supplyType': 'O',
            'subSupplyType': '10',
            'docType': 'CHL',
            'transactionType': 1,
            'transDistance': '0',
            'docNo': 'compa/OUT/00001',
            'docDate': '26/04/2024',
            'fromGstin': 'URP',
            'toGstin': '27DJMPM8965E1ZE',
            'fromTrdName': 'company_1_data',
            'toTrdName': 'partner_a',
            'fromStateCode': 24,
            'toStateCode': 27,
            'fromAddr1': '',
            'toAddr1': '',
            'fromAddr2': '',
            'toAddr2': '',
            'fromPlace': '',
            'toPlace': '',
            'fromPincode': 380004,
            'toPincode': 431122,
            'actToStateCode': 27,
            'actFromStateCode': 24,
            'itemList': [{
                'productName': 'product_a',
                'hsnCode': '01111',
                'productDesc': 'product_a',
                'quantity': 5.0,
                'qtyUnit': 'UNT',
                'taxableAmount': 2500.0,
                'igstRate': 5.0,
            }],
            'totalValue': 2500.0,
            'cgstValue': 0.0,
            'sgstValue': 0.0,
            'igstValue': 125.0,
            'cessValue': 0.0,
            'cessNonAdvolValue': 0.0,
            'otherValue': 0.0,
            'totInvValue': 2625.0
        }
        self.assertDictEqual(ewaybill._ewaybill_generate_direct_json(), expected_json)
