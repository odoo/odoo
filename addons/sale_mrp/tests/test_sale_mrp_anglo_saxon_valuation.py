# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest import skip

from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.addons.stock_account.tests.test_anglo_saxon_valuation_reconciliation_common import ValuationReconciliationTestCommon


@tagged('post_install', '-at_install')
@skip('Temporary to fast merge new valuation')
class TestSaleMRPAngloSaxonValuation(TestSaleCommon, ValuationReconciliationTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.user.company_id.anglo_saxon_accounting = True

    @classmethod
    def _create_product(cls, **create_vals):
        if create_vals.get('is_storable'):
            create_vals['categ_id'] = cls.stock_account_product_categ.id
        return super()._create_product(**create_vals)

    def test_sale_mrp_kit_bom_cogs(self):
        """Check invoice COGS aml after selling and delivering a product
        with Kit BoM having another product with Kit BoM as component"""
        # ----------------------------------------------
        # BoM of Kit A:
        #   - BoM Type: Kit
        #   - Quantity: 3
        #   - Components:
        #     * 2 x Kit B
        #     * 1 x Component A (Cost: $3, Storable)
        #
        # BoM of Kit B:
        #   - BoM Type: Kit
        #   - Quantity: 10
        #   - Components:
        #     * 2 x Component B (Cost: $4, Storable)
        #     * 3 x Component BB (Cost: $5, Consumable)
        # ----------------------------------------------

        self.component_a = self._create_product(name='Component A', is_storable=True, standard_price=3.00)
        self.component_b = self._create_product(name='Component B', is_storable=True, standard_price=4.00)
        self.component_bb = self._create_product(name='Component BB', is_storable=False, standard_price=5.00)
        self.kit_a = self._create_product(name='Kit A', is_storable=True, standard_price=0.00)
        self.kit_b = self._create_product(name='Kit B', is_storable=False, standard_price=0.00)

        self.kit_a.write({
            'property_account_expense_id': self.company_data['default_account_expense'].id,
            'property_account_income_id': self.company_data['default_account_revenue'].id,
        })

        # Create BoM for Kit A
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_tmpl_id = self.kit_a.product_tmpl_id
        bom_product_form.product_qty = 3.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.kit_b
            bom_line.product_qty = 2.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_a
            bom_line.product_qty = 1.0
        self.bom_a = bom_product_form.save()

        # Create BoM for Kit B
        bom_product_form = Form(self.env['mrp.bom'])
        bom_product_form.product_tmpl_id = self.kit_b.product_tmpl_id
        bom_product_form.product_qty = 10.0
        bom_product_form.type = 'phantom'
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_b
            bom_line.product_qty = 2.0
        with bom_product_form.bom_line_ids.new() as bom_line:
            bom_line.product_id = self.component_bb
            bom_line.product_qty = 3.0
        self.bom_b = bom_product_form.save()

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': self.kit_a.name,
                    'product_id': self.kit_a.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 1,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()
        so.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        so.picking_ids.button_validate()

        invoice = so.with_context(default_journal_id=self.company_data['default_journal_sale'].id)._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertAlmostEqual(stock_out_aml.credit, 1.53, msg="Should not include the value of consumable component")
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertAlmostEqual(cogs_aml.debit, 1.53, msg="Should not include the value of consumable component")
        self.assertEqual(cogs_aml.credit, 0)

    def test_sale_mrp_anglo_saxon_variant(self):
        """Test the price unit of kit with variants"""
        # Check that the correct bom are selected when computing price_unit for COGS

        self.env.company.currency_id = self.env.ref('base.USD')

        # Create variant attributes
        self.prod_att_1 = self.env['product.attribute'].create({'name': 'Color'})
        self.prod_attr1_v1 = self.env['product.attribute.value'].create({'name': 'red', 'attribute_id': self.prod_att_1.id, 'sequence': 1})
        self.prod_attr1_v2 = self.env['product.attribute.value'].create({'name': 'blue', 'attribute_id': self.prod_att_1.id, 'sequence': 2})

        # Create Product template with variants
        self.product_template = self.env['product.template'].create({
            'name': 'Product Template',
            'is_storable': True,
            'uom_id': self.uom_unit.id,
            'invoice_policy': 'delivery',
            'categ_id': self.stock_account_product_categ.id,
            'attribute_line_ids': [(0, 0, {
                'attribute_id': self.prod_att_1.id,
                'value_ids': [(6, 0, [self.prod_attr1_v1.id, self.prod_attr1_v2.id])]
            })]
        })

        # Get product variant
        self.pt_attr1_v1 = self.product_template.attribute_line_ids[0].product_template_value_ids[0]
        self.pt_attr1_v2 = self.product_template.attribute_line_ids[0].product_template_value_ids[1]
        self.variant_1 = self.product_template._get_variant_for_combination(self.pt_attr1_v1)
        self.variant_2 = self.product_template._get_variant_for_combination(self.pt_attr1_v2)

        def create_simple_bom_for_product(product, name, price):
            component = self.env['product.product'].create({
                'name': 'Component ' + name,
                'is_storable': True,
                'uom_id': self.uom_unit.id,
                'categ_id': self.stock_account_product_categ.id,
                'standard_price': price
            })
            self.env['stock.quant'].sudo().create({
                'product_id': component.id,
                'location_id': self.company_data['default_warehouse'].lot_stock_id.id,
                'quantity': 10.0,
            })
            bom = self.env['mrp.bom'].create({
                'product_tmpl_id': self.product_template.id,
                'product_id': product.id,
                'product_qty': 1.0,
                'type': 'phantom'
            })
            self.env['mrp.bom.line'].create({
                'product_id': component.id,
                'product_qty': 1.0,
                'bom_id': bom.id
            })

        create_simple_bom_for_product(self.variant_1, "V1", 20)
        create_simple_bom_for_product(self.variant_2, "V2", 10)

        def create_post_sale_order(product):
            so_vals = {
                'partner_id': self.partner_a.id,
                'partner_invoice_id': self.partner_a.id,
                'partner_shipping_id': self.partner_a.id,
                'order_line': [(0, 0, {
                    'name': product.name,
                    'product_id': product.id,
                    'product_uom_qty': 2,
                    'price_unit': product.list_price
                })],
                'company_id': self.company_data['company'].id,
            }
            so = self.env['sale.order'].create(so_vals)
            # Validate the SO
            so.action_confirm()
            # Deliver the three finished products
            pick = so.picking_ids
            # To check the products on the picking
            pick.button_validate()
            # Create the invoice
            so._create_invoices()
            invoice = so.invoice_ids
            invoice.action_post()
            return invoice

        # Create a SO for variant 1
        self.invoice_1 = create_post_sale_order(self.variant_1)
        self.invoice_2 = create_post_sale_order(self.variant_2)

        def check_cogs_entry_values(invoice, expected_value):
            aml = invoice.line_ids
            aml_expense = aml.filtered(lambda l: l.display_type == 'cogs' and l.debit > 0)
            aml_output = aml.filtered(lambda l: l.display_type == 'cogs' and l.credit > 0)
            self.assertEqual(aml_expense.debit, expected_value, "Cost of Good Sold entry missing or mismatching for variant")
            self.assertEqual(aml_output.credit, expected_value, "Cost of Good Sold entry missing or mismatching for variant")

        # Check that the cost of Good Sold entries for variant 1 are equal to 2 * 20 = 40
        check_cogs_entry_values(self.invoice_1, 40)
        # Check that the cost of Good Sold entries for variant 2 are equal to 2 * 10 = 20
        check_cogs_entry_values(self.invoice_2, 20)

    def test_anglo_saxo_return_and_credit_note(self):
        """
        When posting a credit note for a returned kit, the value of the anglo-saxo lines
        should be based on the returned component's value
        """
        self.stock_account_product_categ.property_cost_method = 'fifo'

        kit = self._create_product(name='Simple Kit', is_storable=True, standard_price=0)
        component = self._create_product(name='Compo A', is_storable=True, standard_price=0)
        kit.property_account_expense_id = self.company_data['default_account_expense']

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1.0})]
        })

        # Receive 3 components: one @10, one @20 and one @60
        in_moves = self.env['stock.move'].create([{
            'product_id': component.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': component.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in [10, 20, 60]])
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Sell 3 kits
        so = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [
                (0, 0, {
                    'name': kit.name,
                    'product_id': kit.id,
                    'product_uom_qty': 3.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Deliver the components: 1@10, then 1@20 and then 1@60
        pickings = []
        picking = so.picking_ids
        while picking:
            pickings.append(picking)
            picking.move_ids.write({'quantity': 1, 'picked': True})
            action = picking.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
            picking = picking.backorder_ids

        invoice = so._create_invoices()
        invoice.action_post()

        # Receive one @100
        in_moves = self.env['stock.move'].create({
            'product_id': component.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': component.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Return the second picking (i.e. one component @20)
        ctx = {'active_id': pickings[1].id, 'active_model': 'stock.picking'}
        return_wizard = Form(self.env['stock.return.picking'].with_context(ctx)).save()
        return_wizard.product_return_moves.quantity = 1
        return_picking = return_wizard._create_return()
        return_picking.move_ids.write({'quantity': 1, 'picked': True})
        return_picking.button_validate()

        # Add a credit note for the returned kit
        ctx = {'active_model': 'account.move', 'active_ids': invoice.ids}
        refund_wizard = self.env['account.move.reversal'].with_context(ctx).create({
            'journal_id': invoice.journal_id.id,
        })
        action = refund_wizard.refund_moves()
        reverse_invoice = self.env['account.move'].browse(action['res_id'])
        with Form(reverse_invoice) as reverse_invoice_form:
            with reverse_invoice_form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        reverse_invoice.action_post()

        amls = reverse_invoice.line_ids
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 20, 'Should be to the value of the returned component')
        self.assertEqual(stock_out_aml.credit, 0)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 0)
        self.assertEqual(cogs_aml.credit, 20, 'Should be to the value of the returned component')

    def test_anglo_saxo_return_and_create_invoice(self):
        """
        When creating an invoice for a returned kit, the value of the anglo-saxo lines
        should be based on the returned component's value
        """
        self.stock_account_product_categ.property_cost_method = 'fifo'

        kit = self._create_product(name='Simple Kit', is_storable=True, standard_price=0)
        component = self._create_product(name='Compo A', is_storable=True, standard_price=0)
        (kit + component).invoice_policy = 'delivery'
        kit.property_account_expense_id = self.company_data['default_account_expense']

        self.env['mrp.bom'].create({
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [(0, 0, {'product_id': component.id, 'product_qty': 1.0})]
        })

        # Receive 3 components: one @10, one @20 and one @60
        in_moves = self.env['stock.move'].create([{
            'product_id': component.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': component.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': p,
        } for p in [10, 20, 60]])
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Sell 3 kits
        so = self.env['sale.order'].create({
            'partner_id': self.env['res.partner'].create({'name': 'Test Partner'}).id,
            'order_line': [
                (0, 0, {
                    'name': kit.name,
                    'product_id': kit.id,
                    'product_uom_qty': 3.0,
                    'price_unit': 100,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()

        # Deliver the components: 1@10, then 1@20 and then 1@60
        pickings = []
        picking = so.picking_ids
        while picking:
            pickings.append(picking)
            picking.move_ids.write({'quantity': 1, 'picked': True})
            action = picking.button_validate()
            if isinstance(action, dict):
                Form.from_action(self.env, action).save().process()
            picking = picking.backorder_ids

        invoice = so._create_invoices()
        invoice.action_post()

        # Receive one @100
        in_moves = self.env['stock.move'].create({
            'product_id': component.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.company_data['default_warehouse'].lot_stock_id.id,
            'product_uom': component.uom_id.id,
            'product_uom_qty': 1,
            'price_unit': 100,
        })
        in_moves._action_confirm()
        in_moves.write({'quantity': 1, 'picked': True})
        in_moves._action_done()

        # Return the second picking (i.e. one component @20)
        ctx = {'active_id': pickings[1].id, 'active_model': 'stock.picking'}
        return_wizard = Form(self.env['stock.return.picking'].with_context(ctx)).save()
        return_wizard.product_return_moves.quantity = 1
        return_picking = return_wizard._create_return()
        return_picking.move_ids.write({'quantity': 1, 'picked': True})
        return_picking.button_validate()

        # Create a new invoice for the returned kit
        ctx = {'active_model': 'sale.order', 'active_ids': so.ids}
        create_invoice_wizard = self.env['sale.advance.payment.inv'].with_context(ctx).create(
            {'advance_payment_method': 'delivered'})
        create_invoice_wizard.create_invoices()
        reverse_invoice = so.invoice_ids[-1]
        with Form(reverse_invoice) as reverse_invoice_form:
            with reverse_invoice_form.invoice_line_ids.edit(0) as line:
                line.quantity = 1
        reverse_invoice.action_post()

        amls = reverse_invoice.line_ids
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 20, 'Should be to the value of the returned component')
        self.assertEqual(stock_out_aml.credit, 0)
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertEqual(cogs_aml.debit, 0)
        self.assertEqual(cogs_aml.credit, 20, 'Should be to the value of the returned component')

    def test_kit_avco_fully_owned_and_delivered_invoice_post_delivery(self):
        self.stock_account_product_categ.property_cost_method = 'average'

        compo01 = self._create_product(name='Compo 01', is_storable=True, standard_price=10)
        compo02 = self._create_product(name='Compo 02', is_storable=True, standard_price=20)
        kit = self._create_product(name='Kit', is_storable=True, standard_price=0)

        (compo01 + compo02 + kit).invoice_policy = 'delivery'

        self.env['stock.quant']._update_available_quantity(compo01, self.company_data['default_warehouse'].lot_stock_id, 1, owner_id=self.partner_b)
        self.env['stock.quant']._update_available_quantity(compo02, self.company_data['default_warehouse'].lot_stock_id, 1, owner_id=self.partner_b)

        self.env['mrp.bom'].create({
            'product_id': kit.id,
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_uom_id': kit.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': compo02.id, 'product_qty': 1.0}),
            ],
        })

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': kit.name,
                    'product_id': kit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 5,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()
        so.picking_ids.move_ids.write({'quantity': 1, 'picked': True})
        so.picking_ids.button_validate()

        invoice = so._create_invoices()
        invoice.action_post()

        # COGS should not exist because the products are owned by an external partner
        amls = invoice.line_ids
        self.assertRecordValues(amls, [
            # pylint: disable=bad-whitespace
            {'account_id': self.company_data['default_account_revenue'].id,     'debit': 0,     'credit': 5},
            {'account_id': self.company_data['default_account_receivable'].id,  'debit': 5,     'credit': 0},
        ])

    def test_kit_avco_partially_owned_and_delivered_invoice_post_delivery(self):
        self.stock_account_product_categ.property_cost_method = 'average'

        compo01 = self._create_product(name='Compo 01', is_storable=True, standard_price=10)
        compo02 = self._create_product(name='Compo 02', is_storable=True, standard_price=20)
        kit = self._create_product(name='Kit', is_storable=True, standard_price=0)

        (compo01 + compo02 + kit).invoice_policy = 'delivery'

        self.env['stock.quant']._update_available_quantity(compo01, self.company_data['default_warehouse'].lot_stock_id, 1, owner_id=self.partner_b)
        self.env['stock.quant']._update_available_quantity(compo01, self.company_data['default_warehouse'].lot_stock_id, 1)
        self.env['stock.quant']._update_available_quantity(compo02, self.company_data['default_warehouse'].lot_stock_id, 1, owner_id=self.partner_b)
        self.env['stock.quant']._update_available_quantity(compo02, self.company_data['default_warehouse'].lot_stock_id, 1)

        self.env['mrp.bom'].create({
            'product_id': kit.id,
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_uom_id': kit.uom_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': compo01.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': compo02.id, 'product_qty': 1.0}),
            ],
        })

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': kit.name,
                    'product_id': kit.id,
                    'product_uom_qty': 2.0,
                    'price_unit': 5,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()
        so.picking_ids.move_line_ids.quantity = 1
        so.picking_ids.move_ids.picked = True
        so.picking_ids.button_validate()

        invoice = so._create_invoices()
        invoice.action_post()

        # COGS should not exist because the products are owned by an external partner
        amls = invoice.line_ids
        self.assertRecordValues(amls, [
            # pylint: disable=bad-whitespace
            {'account_id': self.company_data['default_account_revenue'].id,     'debit': 0,     'credit': 10},
            {'account_id': self.company_data['default_account_receivable'].id,  'debit': 10,    'credit': 0},
            {'account_id': self.company_data['default_account_stock_out'].id,   'debit': 0,     'credit': 30},
            {'account_id': self.company_data['default_account_expense'].id,     'debit': 30,    'credit': 0},
        ])

    def test_anglo_saxo_kit_subkits(self):
        """Check invoice COGS aml after selling and delivering a product
        with Kit BoM producing 2 times the product and having
        2 products with Kit BoM as components"""

        # ----------------------------------------------
        # BoM of Main kit:
        #   - BoM Type: Kit
        #   - Quantity: 4
        #   - Components:
        #     * 1 x Subkit A
        #     * 1 x Subkit B
        #
        # BoM of Subkit A:
        #   - BoM Type: Kit
        #   - Quantity: 1
        #   - Components:
        #     * 2 x Component A (Cost: $10, Storable)
        #
        # BoM of Subkit B:
        #   - BoM Type: Kit
        #   - Quantity: 1
        #   - Components:
        #     * 2 x Component B (Cost: $6, Storable)
        # ----------------------------------------------

        component_a = self._create_product(name='Component A', is_storable=True, standard_price=10.00)
        component_b = self._create_product(name='Component B', is_storable=True, standard_price=6.00)
        subkit_a = self._create_product(name='Subkit A', is_storable=True, standard_price=0.00)
        subkit_b = self._create_product(name='Subkit B', is_storable=True, standard_price=0.00)
        main_kit = self._create_product(name='Main kit', is_storable=True, standard_price=0.00)

        main_kit.write({
            'property_account_expense_id': self.company_data['default_account_expense'].id,
            'property_account_income_id': self.company_data['default_account_revenue'].id,
        })

        # Create BoM for Main kit
        self.env['mrp.bom'].create({
            'product_id': main_kit.id,
            'product_tmpl_id': main_kit.product_tmpl_id.id,
            'product_qty': 4.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': subkit_a.id, 'product_qty': 1.0}),
                (0, 0, {'product_id': subkit_b.id, 'product_qty': 1.0}),
            ],
        })
        # Create BoM for Subkit A
        self.env['mrp.bom'].create({
            'product_id': subkit_a.id,
            'product_tmpl_id': subkit_a.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': component_a.id, 'product_qty': 2.0}),
            ],
        })
        # Create BoM for Subkit B
        self.env['mrp.bom'].create({
            'product_id': subkit_b.id,
            'product_tmpl_id': subkit_b.product_tmpl_id.id,
            'product_qty': 1.0,
            'type': 'phantom',
            'bom_line_ids': [
                (0, 0, {'product_id': component_b.id, 'product_qty': 2.0}),
            ],
        })

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                (0, 0, {
                    'name': main_kit.name,
                    'product_id': main_kit.id,
                    'product_uom_qty': 1.0,
                    'price_unit': 1,
                    'tax_ids': False,
                })],
        })
        so.action_confirm()
        for move in so.picking_ids.move_ids:
            move.quantity = move.product_uom_qty
        so.picking_ids.button_validate()

        invoice = so.with_context(default_journal_id=self.company_data['default_journal_sale'].id)._create_invoices()
        invoice.action_post()

        # Check the resulting accounting entries
        amls = invoice.line_ids
        self.assertEqual(len(amls), 4)
        stock_out_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_stock_out'])
        self.assertEqual(stock_out_aml.debit, 0)
        self.assertAlmostEqual(stock_out_aml.credit, 8.00, msg="Should include include the components from all subkits, with the price adapted for 1 Main kit")
        cogs_aml = amls.filtered(lambda aml: aml.account_id == self.company_data['default_account_expense'])
        self.assertAlmostEqual(cogs_aml.debit, 8.00, msg="Should include include the components from all subkits, with the price adapted for 1 Main kit")
        self.assertEqual(cogs_aml.credit, 0)

    def test_sell_kit_invoice_before_delivery(self):
        """ When a kit product is invoiced prior to delivery, we want to make sure to reconcile all
        the AMLs from its explosion together, else we risk re-reconciliation attempts (which will
        block certain actions from being performed altogether).
        """
        self.stock_account_product_categ.property_cost_method = 'average'

        compo01 = self._create_product(name="Compo 01", is_storable=True, standard_price=10)
        compo02 = self._create_product(name="Compo 02", is_storable=True, standard_price=20)
        kit = self._create_product(name="Kit", is_storable=True, standard_price=30)
        (compo01 + compo02 + kit).write({'invoice_policy': 'order'})
        warehouse = self.company_data['default_warehouse']
        self.env['stock.quant']._update_available_quantity(compo01, warehouse.lot_stock_id, 1.0)
        self.env['stock.quant']._update_available_quantity(compo02, warehouse.lot_stock_id, 2.0)
        self.env['mrp.bom'].create({
            'type': 'phantom',
            'product_id': kit.id,
            'product_tmpl_id': kit.product_tmpl_id.id,
            'product_qty': 1,
            'bom_line_ids': [
                Command.create({'product_id': compo01.id, 'product_qty': 1}),
                Command.create({'product_id': compo02.id, 'product_qty': 1}),
            ],
        })
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': kit.id,
                    'product_uom_qty': 1,
                    'price_unit': 10,
                }),
                Command.create({
                    'product_id': compo02.id,
                    'product_uom_qty': 1,
                    'price_unit': 5,
                }),
            ],
        })
        sale_order.action_confirm()
        invoice = sale_order.with_context(default_journal_id=self.company_data['default_journal_sale'].id)._create_invoices()
        invoice.action_post()
        delivery = sale_order.picking_ids
        # would fail due to attempted re-reconciliation prior to this commit
        delivery.button_validate()
        stock_output_amls = self.env['account.move.line'].search([('account_id', '=', self.company_data['default_account_stock_out'].id)], order='id asc')
        self.assertRecordValues(stock_output_amls,
            [
                {'product_id': kit.id,       'reconciled': True,    'debit': 0.0,     'credit':  30.0},
                {'product_id': compo02.id,   'reconciled': True,    'debit': 0.0,     'credit':  20.0},
                {'product_id': compo01.id,   'reconciled': True,    'debit': 10.0,    'credit':  0.0},
                {'product_id': compo02.id,   'reconciled': True,    'debit': 20.0,    'credit':  0.0},
                {'product_id': compo02.id,   'reconciled': True,    'debit': 20.0,    'credit':  0.0},
            ]
        )
