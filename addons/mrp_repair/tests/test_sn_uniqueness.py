# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo.addons.mrp.tests.common import TestMrpCommon
from odoo.addons.stock.models.stock_location import Location
from odoo.exceptions import UserError
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestSNUniqueness(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        """ Sets up a BoM with a single SN tracked component. """
        super().setUpClass()
        cls.component = cls.env['product.product'].create({
            'name': 'Product serial',
            'type': 'product',
            'tracking': 'serial',
            'categ_id': cls.env.ref('product.product_category_all').id,
        })
        cls.bom = cls.env['mrp.bom'].create({
            'product_id': cls.product_1.id,
            'product_tmpl_id': cls.product_1.product_tmpl_id.id,
            'product_uom_id': cls.env.ref('uom.product_uom_unit').id,
            'product_qty': 1.0,
            'type': 'normal',
            'bom_line_ids': [
                (0, 0, {'product_id': cls.component.id, 'product_qty': 1}),
            ],
        })

        cls.stock_location = cls.env.ref('stock.stock_location_stock').id
        cls.production_location = cls.env['stock.location'].search([
            ('usage', '=', 'production')
        ], limit=1).id

    def _create_mo(self, lot):
        """ Creates an MO and assigns the given lot to the stock move. """
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.product_1
        mo_form.bom_id = self.bom
        mo_form.product_uom_id = self.env.ref('uom.product_uom_unit')
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()
        mo.qty_producing = 1
        mo.move_raw_ids.lot_ids = lot
        for ml in mo.move_raw_ids.move_line_ids:
            ml.lot_id = lot
            ml.quant_id = self.env['stock.quant'].create({
                'location_id': self.stock_location,
                'product_id': self.component.id,
                'lot_id': lot.id
            })
        return mo

    def _create_mo_and_validate(self, lot):
        """
        Creates an MO and assigns the given lot to the stock move, then marks
        the MO as done and returns warnings from validating stock move lines.
        """
        mo = self._create_mo(lot)
        warning = mo.move_raw_ids._onchange_move_line_ids_mrp()
        mo.mark_done()
        self.assertEqual(mo.state, 'done')

        return warning

    def _create_ro(self, lot):
        """ Creates a repair and assigns the given lot to the stock move. """
        with Form(self.env['repair.order']) as ro_form:
            ro_form.product_id = self.product_1
            with ro_form.move_ids.new() as operation:
                operation.repair_line_type = 'add'
                operation.product_id = self.component
            ro = ro_form.save()

        ro.action_validate()
        ro.move_ids.lot_ids = lot
        for ml in ro.move_ids.move_line_ids:
            ml.lot_id = lot
            ml.quant_id = self.env['stock.quant'].create({
                'location_id': self.stock_location,
                'product_id': self.component.id,
                'lot_id': lot.id
            })

        return ro

    def _create_ro_and_validate(self, lot):
        """
        Creates a repair and assigns the given lot to the stock move, then marks
        the repair as done and returns warnings from validating stock move lines.
        """
        ro = self._create_ro(lot)
        warning = ro.move_ids._onchange_move_line_ids_repair()
        ro.action_repair_start()
        ro.action_repair_end()
        self.assertEqual(ro.state, 'done')

        return warning

    def _create_lot_with_quant(self, product, lot_name):
        """ Creates a new lot for the given product and adds one product to stock. """
        lot = self.env['stock.lot'].create({
            'name': lot_name,
            'product_id': product.id,
        })
        quant = self.env['stock.quant'].create({
            'location_id': self.stock_location,
            'product_id': product.id,
            'inventory_quantity': 1,
            'lot_id': lot.id
        })
        quant.action_apply_inventory()

        return lot

    def _add_stock_move_line(self, stock_move):
        """ Appends a new line to given stock move lines. """
        details_operation_form = Form(
            stock_move, view=self.env.ref('stock.view_stock_move_operations')
        )
        with details_operation_form.move_line_ids.new():
            # TODO find a better way to add a new stock move line
            pass
        details_operation_form.save()

    def _assert_sn_warning(self, warning):
        """ Checks if the warning is the one about reusing SN products. """
        self.assertEqual(warning, {
            'warning': {
                'title': 'Warning',
                'message': (
                    'This serial number has already been consumed before. '
                    'Double check that this is accurate before moving on.'
                )
            }
        })

    def _assert_quantities(self, product, expected_quantities):
        """
        Checks if given product's quantities in different locations are correct.
        `expected_quantities` is a dictionary of location usage to quantity.
        """
        # Merge the quants first
        for usage in [l[0] for l in Location.usage.selection]:
            quant = self.env['stock.quant'].search([
                ('product_id', '=', product.id), ('location_id.usage', '=', usage)
            ], limit=1)
            quant._merge_quants()

        # Group the quantities by location, in case there are multiple lots
        quantities_per_location = defaultdict(int)
        for quant in self.env['stock.quant'].search([('product_id', '=', product.id)]):
            quantities_per_location[quant.location_id.usage] += quant.quantity

        # Compare with expected values
        self.assertEqual(dict(quantities_per_location), expected_quantities)

    def test_use_sn_product_twice(self):
        """
        Using an SN product for the first time should not return any warnings.
        Using it for the second time should display a warning, but not prevent
        the user from completing the order. After the second order is marked as
        done, product's quantities should be updated accordingly, resulting in
        negative value in stock.

        This should work both for MOs and for repairs.
        """
        order_combinations = [
            ('mo', 'mo'),
            ('mo', 'ro'),
            ('ro', 'ro'),
            ('ro', 'mo'),
        ]
        for order_type_1, order_type_2 in order_combinations:
            with self.subTest(f'{order_type_1} {order_type_2}'):
                # Create one lot with one product
                lot = self._create_lot_with_quant(self.component, 'S1')

                self._assert_quantities(self.component, {
                    'internal': 1,
                    'inventory': -1,
                })

                if order_type_1 == 'mo':
                    warning = self._create_mo_and_validate(lot)
                elif order_type_1 == 'ro':
                    warning = self._create_ro_and_validate(lot)

                # Component is available, so there should be no warning
                self.assertEqual(warning, {})

                # Component should be subtracted from stock
                self._assert_quantities(self.component, {
                    'internal': 0,
                    'inventory': -1,
                    'production': 1,
                })

                if order_type_2 == 'mo':
                    warning = self._create_mo_and_validate(lot)
                elif order_type_2 == 'ro':
                    warning = self._create_ro_and_validate(lot)

                # Component is no longer available, there should be a warning
                self._assert_sn_warning(warning)

                self._assert_quantities(self.component, {
                    'internal': -1,
                    'inventory': -1,
                    'production': 2,
                })

                # Clean up before the next subTest
                lot.quant_ids.unlink()
                lot.unlink()

    def test_reuse_sn_product_and_unbuild(self):
        """
        After an SN product is used twice, it should be possible to unbuild one
        of the MOs and get the product back, returning the quantities to the
        values after the first MO was completed.
        """
        lot = self._create_lot_with_quant(self.component, 'S1')

        # Create 2 MOs
        self._create_mo_and_validate(lot)
        mo = self._create_mo(lot)
        mo.mark_done()

        self._assert_quantities(self.component, {
            'internal': -1,
            'inventory': -1,
            'production': 2,
        })

        # Unbuild the last MO
        uo_form = Form(self.env['mrp.unbuild'])
        uo_form.mo_id = mo
        uo_form.product_qty = 1
        uo = uo_form.save()
        uo.action_unbuild()
        self.assertEqual(uo.state, 'done')

        # Component should be returned
        self._assert_quantities(self.component, {
            'internal': 0,
            'inventory': -1,
            'production': 1,
        })

    def test_reuse_sn_product_with_multiple_lots(self):
        """
        In case a product has multiple lots, there should be no warning when a
        full lot is used in an MO, even if another lot is already empty. Using
        the product from an empty lot should still result in a warning.
        """
        # Create two lots, each with one product
        lot_1 = self._create_lot_with_quant(self.component, 'S1')
        lot_2 = self._create_lot_with_quant(self.component, 'S2')

        self._assert_quantities(self.component, {
            'internal': 2,
            'inventory': -2,
        })

        # Lot 1 used for the first time, no warning
        warning = self._create_mo_and_validate(lot_1)
        self.assertEqual(warning, {})

        # Lot 2 used for the first time, no warning
        warning = self._create_mo_and_validate(lot_2)
        self.assertEqual(warning, {})

        self._assert_quantities(self.component, {
            'internal': 0,
            'inventory': -2,
            'production': 2,
        })

        # Lot 1 used for the second time, warning
        warning = self._create_mo_and_validate(lot_1)
        self._assert_sn_warning(warning)

        # Lot 2 used for the second time, warning
        warning = self._create_mo_and_validate(lot_2)
        self._assert_sn_warning(warning)

        self._assert_quantities(self.component, {
            'internal': -2,
            'inventory': -2,
            'production': 4,
        })

    def test_add_sn_product_twice_to_the_same_mo(self):
        """
        Reusing the same SN product twice in a single MO is considered wrong
        and should result in an error.
        """
        lot = self._create_lot_with_quant(self.component, 'S1')

        # Create MO with 2 components
        mo = self._create_mo(lot)
        mo.qty_producing = 2
        self._add_stock_move_line(mo.move_raw_ids)
        self.assertEqual(len(mo.move_raw_ids.move_line_ids), 2)

        # Set lot and quant for the new line
        for ml in mo.move_raw_ids.move_line_ids:
            ml.lot_id = lot
            ml.quant_id = self.env['stock.quant'].create({
                'location_id': self.stock_location,
                'product_id': self.component.id,
                'lot_id': lot.id
            })

        # SN components can be reused, but not within the same order
        with self.assertRaises(UserError) as error:
            mo.move_raw_ids._onchange_move_line_ids_mrp()

        self.assertEqual(
            str(error.exception),
            'You cannot use the same serial number twice in one order.'
        )

    def test_add_sn_product_twice_to_the_same_ro(self):
        """
        Reusing the same SN product twice in a single repair is considered wrong
        and should result in an error.
        """
        lot = self._create_lot_with_quant(self.component, 'S1')

        # Create RO with 2 components
        ro = self._create_ro(lot)
        self._add_stock_move_line(ro.move_ids)
        self.assertEqual(len(ro.move_ids.move_line_ids), 2)

        # Set lot and quant for the new line
        for ml in ro.move_ids.move_line_ids:
            ml.lot_id = lot
            ml.quant_id = self.env['stock.quant'].create({
                'location_id': self.stock_location,
                'product_id': self.component.id,
                'lot_id': lot.id
            })

        # SN components can be reused, but not within the same order
        with self.assertRaises(UserError) as error:
            ro.move_ids._onchange_move_line_ids_repair()

        self.assertEqual(
            str(error.exception),
            'You cannot use the same serial number twice in one order.'
        )

    def test_reuse_sn_product_after_manual_stock_move(self):
        """
        After an MO is confirmed, the SN product can be moved manually from
        production back to stock. In that case, the second MO should not return
        any warnings (the component is available again).
        """
        lot = self._create_lot_with_quant(self.component, 'S1')

        # Create the first MO with the component still available
        self._create_mo_and_validate(lot)

        # Move the component manually back from prod to stock
        move1 = self.env['stock.move'].create({
            'name': 'test_in_date_1',
            'location_id': self.production_location,
            'location_dest_id': self.stock_location,
            'product_id': self.component.id,
            'product_uom': self.env.ref('uom.product_uom_unit').id,
            'product_uom_qty': 1.0,
            'picking_type_id': self.env.ref('stock.picking_type_in').id,
        })
        move1._action_confirm()
        move1._action_assign()
        move1.move_line_ids.lot_id = lot
        move1.move_line_ids.qty_done = 1
        move1._action_done()

        self._assert_quantities(self.component, {
            'internal': 1,
            'inventory': -1,
            'production': 0,
        })

        # Since the component is available again, there should be no warning
        warning = self._create_mo_and_validate(lot)
        self.assertEqual(warning, {})

        # Stock values are the same as they were after the first MO
        self._assert_quantities(self.component, {
            'internal': 0,
            'inventory': -1,
            'production': 1,
        })
