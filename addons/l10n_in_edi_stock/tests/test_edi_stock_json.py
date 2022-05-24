# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged("post_install_l10n", "post_install", "-at_install")
class TestEdiStockJson(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref="l10n_in.indian_chart_template_standard"):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.maxDiff = None
        cls.company_data["company"].write({
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 1",
            "zip": "247667",
            "state_id": cls.env.ref("base.state_in_uk").id,
            "country_id": cls.env.ref("base.in").id,
            "vat": "05AAACH6188F1ZM",
        })
        cls.partner_a.write({
            "vat": "05AAACH6605F1Z0",
            "street": "Block no. 401",
            "street2": "Street 2",
            "city": "City 2",
            "zip": "248001",
            "state_id": cls.env.ref("base.state_in_uk").id,
            "country_id": cls.env.ref("base.in").id,
            "l10n_in_gst_treatment": "regular",
        })
        cls.product_a.write({"type": "product", "l10n_in_hsn_code": "01111"})

        warehouse_id = cls.env['stock.warehouse'].search([('company_id', '=', cls.company_data["company"].id)], limit=1)
        cls.customer_location = cls.env.ref('stock.stock_location_customers')
        cls.picking = cls.env['stock.picking'].create({
            'location_id': warehouse_id.lot_stock_id.id,
            'location_dest_id': cls.customer_location.id,
            'picking_type_id': warehouse_id.out_type_id.id,
            'partner_id': cls.partner_a.id,
            'l10n_in_type_id': cls.env.ref('l10n_in_edi_stock.type_delivery_challan').id,
            'l10n_in_subtype_id': cls.env.ref('l10n_in_edi_stock.type_job_work').id,
            'l10n_in_transaction_type': '1',
            'l10n_in_distance': '50',
            'l10n_in_mode': '1',
            'l10n_in_vehicle_type': 'R',
            'l10n_in_vehicle_no': 'KA12KA1234',
            'move_ids': [(0, 0, {
                'name': cls.product_a.name,
                'product_id': cls.product_a.id,
                'product_uom': cls.product_a.uom_id.id,
                'product_uom_qty': 1.0,
                'location_id': warehouse_id.lot_stock_id.id,
                'location_dest_id': cls.customer_location.id,
                'state': 'confirmed',
                'description_picking': cls.product_a.name,
            })]
        })

        cls.env['stock.quant']._update_available_quantity(cls.product_a, warehouse_id.lot_stock_id, 10.0)
        cls.picking.action_assign()
        cls.picking.action_set_quantities_to_reservation()
        cls.picking.button_validate()
        cls.picking.date_done = fields.Date.from_string('2022-01-01')
        cls.invoice = cls.init_invoice("out_invoice", post=True, products=cls.product_a)

    def test_edi_stock_json(self):
        json_value = self.picking._l10n_in_edi_stock_prepare_json()
        expected = {
            'supplyType': 'O',
            'docNo': 'compa/OUT/00001',
            'docDate': '01/01/2022',
            'fromGstin': '05AAACH6188F1ZM',
            'fromTrdName': 'company_1_data',
            'fromStateCode': 5,
            'fromAddr1': 'Block no. 401',
            'fromAddr2': 'Street 2',
            'fromPlace': 'City 1',
            'fromPincode': 247667,
            'actFromStateCode': 5,
            'toGstin': '05AAACH6605F1Z0',
            'toTrdName': 'partner_a',
            'toStateCode': 5,
            'toAddr1': 'Block no. 401',
            'toAddr2': 'Street 2',
            'toPlace': 'City 2',
            'toPincode': 248001,
            'actToStateCode': 5,
            'itemList': [{
                'productName': 'product_a',
                'hsnCode': '01111',
                'productDesc': 'product_a',
                'quantity': 1.0,
                'qtyUnit': 'UNT',
                'taxableAmount': 1000.0,
                'cgstRate': 2.5,
                'sgstRate': 2.5
            }],
            'totalValue': 1000.0,
            'cgstValue': 25.0,
            'sgstValue': 25.0,
            'igstValue': 0.0,
            'cessValue': 0.0,
            'cessNonAdvolValue': 0.0,
            'otherValue': 0.0,
            'totInvValue': 1050.0,
            'subSupplyType': '4',
            'docType': 'CHL',
            'transactionType': 1,
            'transDistance': '50',
            'transMode': '1',
            'transDocNo': '',
            'vehicleNo': 'KA12KA1234',
            'vehicleType': 'R'
        }
        self.assertDictEqual(json_value, expected, "Indian E-Waybill send json value is not matched")
        self.picking.write({
            'l10n_in_related_invoice_id': self.invoice.id,
            'l10n_in_type_id': self.env.ref('l10n_in_edi_stock.type_tax_invoice').id,
            'l10n_in_subtype_id': self.env.ref('l10n_in_edi_stock.type_supply').id,
        })
        json_value = self.picking._l10n_in_edi_stock_prepare_json()
        expected.update({
                'docNo': 'INV/2019/00001',
                'docDate': '01/01/2019',
                'subSupplyType': '1',
                'docType': 'INV',
            })
        self.assertDictEqual(json_value, expected, "Indian E-Waybill send json value is not matched")
