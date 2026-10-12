from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.l10n_in.tests.common import L10nInTestInvoicingCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestL10nInBoeWizard(L10nInTestInvoicingCommon):

    _test_user_groups = (
        'account.group_account_manager',
        'purchase.group_purchase_user',
        'stock.group_stock_manager',
    )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_foreign.l10n_in_gst_treatment = 'overseas'

        cls.categ_avco = cls.env.ref('product.product_category_goods').copy({
            'property_cost_method': 'average',
        })

        cls.product_a.categ_id = cls.categ_avco.id

        cls.port_code = cls.env['l10n_in.port.code'].search([('code', '=', 'INBOM4')], limit=1)

    def _create_purchase_to_bill(self, partner):
        """ Generate PO -> Receipt -> Vendor Bill """
        po = self.env['purchase.order'].create({
            'partner_id': partner.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_qty': 10.0,
                    'price_unit': 200.0,
                }),
            ],
        })
        po.button_confirm()

        picking = po.picking_ids[0]
        for move in picking.move_ids:
            move.quantity = 10.0
        picking.button_validate()

        po.action_create_invoice()
        bill = po.invoice_ids
        bill.invoice_date = fields.Date.today()
        return picking, bill

    def test_boe_wizard_landed_cost_flow_and_lines(self):
        picking, bill = self._create_purchase_to_bill(self.partner_foreign)
        bill.action_post()

        wizard = self.env['l10n_in.boe.wizard'].with_context(default_move_ids=bill.ids).create({
            'l10n_in_shipping_bill_number': 'BOE12345',
            'l10n_in_shipping_bill_date': fields.Date.today(),
            'l10n_in_shipping_port_code_id': self.port_code.id,
        })

        self.assertRecordValues(wizard.line_ids, [{
            'assessable_value': 2000.0,
            'product_id': self.product_a.id,
            'stock_move_id': picking.move_ids[:1].id,
            'quantity': 10.0,
            'custom_duty': 0.0,
            'tax_ids': [],
            'taxable_amount': 2000.0,
            'tax_amount': 0.0,
        }])
        # Apply Custom Duty
        wizard.line_ids[:1].write({
            'custom_duty': 500.0,
            'tax_ids': [Command.set(self.igst_sale_18.ids)],
        })
        action = wizard.action_on_submit_boe()

        boe_bill = self.env['account.move'].browse(action.get('res_id'))
        boe_bill.partner_id = self.partner_a
        boe_bill.action_post()
        custom_duty_id = self.env['l10n_in.boe.wizard']._get_l10n_in_find_or_create_custom_duty_product().id
        self.assertRecordValues(boe_bill.invoice_line_ids, [
            {
                'product_id': custom_duty_id,
                'tax_ids': self.igst_sale_18.ids,
                'price_unit': 2500.0,
                'quantity': 1,
                'price_total': 2950.0,
                'is_landed_costs_line': True,
            },
            {
                'product_id': custom_duty_id,
                'price_unit': -2000.0,
                'quantity': 1,
                'price_total': -2000.0,
                'tax_ids': [],
                'is_landed_costs_line': True,
            },
        ])

        self.assertEqual(boe_bill.amount_tax, 450.0, "BOE Bill Total Tax should evaluate to 450.0")
        landed_cost = boe_bill.landed_costs_ids
        self.assertTrue(landed_cost, "Landed cost must be generated automatically")
        self.assertEqual(landed_cost.picking_ids, picking, "Landed cost must link back to the PO receipt")

        self.assertRecordValues(landed_cost.valuation_adjustment_lines, [{
            'former_cost': 2000.0,
            'additional_landed_cost': 500.0,
        }])
