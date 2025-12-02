from odoo.fields import Command
from odoo.tests import tagged, common, Form


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestConsumptionWarning(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref('uom.group_uom')
        cls.uom_ml = cls.env.ref('uom.product_uom_milliliter')
        cls.uom_l = cls.env.ref('uom.product_uom_litre')
        cls.uom_m3 = cls.env.ref('uom.product_uom_cubic_meter')
        cls.uom_g = cls.env.ref('uom.product_uom_gram')
        cls.uom_kg = cls.env.ref('uom.product_uom_kgm')
        cls.uom_unit = cls.env.ref('uom.product_uom_unit')
        cls.uom_6 = cls.env.ref('uom.product_uom_pack_6')
        cls.uom_dozen = cls.env.ref('uom.product_uom_dozen')

        cls.soup, cls.pack, cls.seasoning = cls.env['product.product'].create([
            {'name': 'Soup', 'uom_id': cls.uom_l.id},
            {'name': 'Pack of Instant Ramen', 'uom_id': cls.uom_unit.id},
            {'name': 'Seasoning', 'uom_id': cls.uom_unit.id},
        ])

        cls.water, cls.noodles, cls.msg, cls.salt, cls.oil = cls.env['product.product'].create([
            {'name': 'Hot Water', 'uom_id': cls.uom_l.id},
            {'name': 'Dry Noodles', 'uom_id': cls.uom_g.id},
            {'name': 'MSG', 'uom_id': cls.uom_g.id},
            {'name': 'Salt', 'uom_id': cls.uom_g.id},
            {'name': 'Oil', 'uom_id': cls.uom_ml.id},
        ])

        # Nested kit to test successful explosion
        cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.seasoning.product_tmpl_id.id,
            'uom_id': cls.uom_g.id,
            'product_qty': 5,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({'product_id': cls.msg.id, 'product_qty': 2}),
                Command.create({'product_id': cls.salt.id, 'product_qty': 2}),
                Command.create({'product_id': cls.oil.id, 'product_qty': 1}),
            ],
        })
        cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.pack.product_tmpl_id.id,
            'uom_id': cls.uom_dozen.id,
            'product_qty': 2,
            'type': 'phantom',
            'bom_line_ids': [
                Command.create({
                    'product_id': cls.noodles.id,
                    'uom_id': cls.uom_kg.id,
                    'product_qty': 4.8,
                }),
                Command.create({
                    'product_id': cls.seasoning.id,
                    'uom_id': cls.uom_kg.id,
                    'product_qty': 0.12,
                }),
            ],
        })

        # Normal child BoM we don't use, just to make sure it's ignored when checking for kits.
        cls.oxygen, cls.hydrogen = cls.env['product.product'].create([
            {'name': 'Oxygen', 'uom_id': cls.uom_g.id},
            {'name': 'Hydrogen', 'uom_id': cls.uom_kg.id},
        ])
        cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.water.product_tmpl_id.id,
            'uom_id': cls.uom_l.id,
            'product_qty': 10,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({'product_id': cls.oxygen.id, 'product_qty': 1116}),
                Command.create({'product_id': cls.hydrogen.id, 'product_qty': 8855}),
            ],
        })

        cls.soup_recipe = cls.env['mrp.bom'].create({
            'product_tmpl_id': cls.soup.product_tmpl_id.id,
            'uom_id': cls.uom_m3.id,
            'product_qty': 0.25,
            'type': 'normal',
            'bom_line_ids': [
                Command.create({
                    'product_id': cls.water.id,
                    'uom_id': cls.uom_m3.id,
                    'product_qty': 0.2,
                }),
                Command.create({
                    'product_id': cls.pack.id,
                    'uom_id': cls.uom_6.id,
                    'product_qty': 150,
                }),
                Command.create({
                    'product_id': cls.salt.id,
                    'uom_id': cls.uom_kg.id,
                    'product_qty': 5,
                })
            ],
        })

    def _make_mo(self, bom, qty, uom):
        mo_form = Form(self.env['mrp.production'])
        mo_form.bom_id = bom
        mo_form.product_qty = qty
        mo_form.uom_id = uom
        return mo_form.save()

    def test_consumption_warning_with_uom_and_kits(self):
        """Check that the consumption warning wizard does not trigger on false positives."""
        mo = self._make_mo(self.soup_recipe, 5, self.uom_m3)
        mo.action_confirm()
        result = mo.button_mark_done()
        # Make sure there is no warning.
        self.assertIs(result, True, "Base case failed. This wasn't supposed to trigger a warning.")

        # Soup recipe (5 m³, serves 14 285 people)
        ingredients = mo.move_raw_ids
        for ingredient in ingredients:
            if ingredient.product_id == self.msg:
                # 2 g MSG in 5 g seasoning
                # => 0,4 g MSG in 1 g seasoning
                # 0,12 kg seasoning in 2 dozen-packs of ramen
                # => 2 g MSG in 1 pack of ramen
                # 150 six-packs of ramen in 0,25 m³ soup
                # => 3600 packs of ramen in 1 m³ soup => 7200 g MSG in 1 m³ soup
                # 5 m³ soup in our recipe
                # => 36 000 g MSG in our recipe
                self.assertEqual(ingredient.quantity, 36_000, "Consumed component quantity ended up wrong.")
                ingredients -= ingredient
            elif ingredient.product_id == self.salt:
                # From seasoning
                if ingredient.uom_id == self.uom_g:
                    # 2 g salt in 5 g seasoning
                    # => 0,4 g salt in 1 g seasoning
                    # 0,12 kg seasoning in 2 dozen-packs of ramen
                    # => 2 g salt in 1 pack of ramen
                    # 150 six-packs of ramen in 0,25 m³ soup
                    # => 3600 packs of ramen in 1 m³ soup => 7200 g salt in 1 m³ soup
                    # 5 m³ soup in our recipe
                    # => 36 000 g salt in our recipe
                    self.assertEqual(ingredient.quantity, 36_000, "Consumed component quantity ended up wrong.")
                    ingredients -= ingredient
                # From recipe
                elif ingredient.uom_id == self.uom_kg:
                    # 5 kg salt in 0,25 m³ soup
                    # => 20 kg salt in 1 m³ soup
                    # 5 m³ soup in our recipe
                    # => 100 kg salt in our recipe
                    self.assertEqual(ingredient.quantity, 100, "Consumed component quantity ended up wrong.")
                    ingredients -= ingredient
            elif ingredient.product_id == self.noodles:
                # 4,8 kg noodles in 2 dozen-packs of ramen
                # => 0,2 kg noodles in 1 pack of ramen
                # 150 six-packs of ramen in 0,25 m³ soup
                # => 3600 packs of ramen in 1 m³ soup => 720 kg noodles in 1 m³ soup
                # 5 m³ soup in our recipe
                # => 3600 kg noodles in our recipe
                self.assertEqual(ingredient.quantity, 3600, "Consumed component quantity ended up wrong.")
                ingredients -= ingredient
            elif ingredient.product_id == self.oil:
                # 1 mL oil in 5 g seasoning
                # => 0,2 mL oil in 1 g seasoning
                # 0,12 kg seasoning in 2 dozen-packs of ramen
                # => 1 mL oil in 1 pack of ramen
                # 150 six-packs of ramen in 0,25 m³ soup
                # => 3600 packs of ramen in 1 m³ soup => 3600 mL oil in 1 m³ soup
                # 5 m³ soup in our recipe
                # => 18 000 mL oil in our recipe
                self.assertEqual(ingredient.quantity, 18_000, "Consumed component quantity ended up wrong.")
                ingredients -= ingredient
            elif ingredient.product_id == self.water:
                # 0,2 m³ water in 0,25 m³ soup
                # => 0,8 m³ water in 1 m³ soup
                # 5 m³ soup in our recipe
                # => 4 m³ water in our recipe
                self.assertEqual(ingredient.quantity, 4, "Consumed component quantity ended up wrong.")
                ingredients -= ingredient
        self.assertFalse(ingredients, "There are components in the MO that were not accounted for.")

    def test_consumption_warning_with_extra_and_missing_components(self):
        """Check that the consumption wizard triggers on missing components and
        recreates them according to the BoM, as well as detects components that
        aren't a part of the BoM and zeroes their quantities if requested.
        """
        mo = self._make_mo(self.soup_recipe, 5, self.uom_m3)
        mo.action_confirm()

        self.env['stock.move'].create({
            'product_id': self.oxygen.id,
            'uom_id': self.uom_kg.id,
            'product_uom_qty': 2500,
            'raw_material_production_id': mo.id,
        })
        mo.move_raw_ids.filtered(lambda move: move.product_id in (self.msg, self.water)).unlink()

        warning = Form.from_action(self.env, mo.button_mark_done()).save()
        self.assertRecordValues(warning.mrp_consumption_warning_line_ids, [
            {
                'product_id': self.oxygen.id,
                'product_consumed_qty_uom': 2500,
                'product_expected_qty_uom': 0,
            },
            {
                'product_id': self.water.id,
                'product_consumed_qty_uom': 0,
                'product_expected_qty_uom': 4,
            },
            {
                'product_id': self.msg.id,
                'product_consumed_qty_uom': 0,
                'product_expected_qty_uom': 36_000,
            },
        ])
        warning.action_set_qty()

        recreated_moves = mo.move_raw_ids.filtered(lambda move: move.product_id in (self.msg, self.water))
        # The extra move should be kept as-is but no quantity should be consumed.
        self.assertEqual(len(recreated_moves), 2, "The wizard didn't recreate the expected moves.")
        for move in recreated_moves:
            if move.product_id == self.water:
                self.assertEqual(move.product_uom_qty, 4, "The quantity of the recreated move is wrong.")
                self.assertEqual(move.uom_id, self.uom_m3, "The UoM of the recreated move is wrong.")
            elif move.product_id == self.msg:
                self.assertEqual(move.product_uom_qty, 36_000, "The quantity of the recreated move is wrong.")
                self.assertEqual(move.uom_id, self.uom_g, "The UoM of the recreated move is wrong.")
        self.assertEqual(mo.move_raw_ids.filtered(lambda move: move.product_id == self.oxygen).quantity,
                         0, "A foreign component was consumed and the wizard failed to catch it.")

        result = mo.button_mark_done()
        # Make sure there's no warning again.
        self.assertIs(result, True, "The moves the wizard recreated didn't conform to the BoM.")

    def test_consumption_warning_with_flipped_uom_and_wrong_quantity(self):
        """Check that the consumption wizard successfully detects and fixes
        over-/underconsumed quantities whilst taking UoM conversions into
        account."""
        mo = self._make_mo(self.soup_recipe, 5, self.uom_m3)
        mo.action_confirm()

        for move in mo.move_raw_ids:
            if move.product_id == self.water:
                move.uom_id = self.uom_ml
                move.product_uom_qty = 8_000_000
            elif move.product_id == self.msg:
                move.uom_id = self.uom_kg
                move.product_uom_qty = 20

        warning = Form.from_action(self.env, mo.button_mark_done()).save()
        self.assertRecordValues(warning.mrp_consumption_warning_line_ids, [
            {
                'product_id': self.water.id,
                'product_consumed_qty_uom': 8_000_000,
                'product_expected_qty_uom': 4_000_000,
                'uom_id': self.uom_ml.id,
            },
            {
                'product_id': self.msg.id,
                'product_consumed_qty_uom': 20,
                'product_expected_qty_uom': 36,
                'uom_id': self.uom_kg.id,
            },
        ])
        warning.action_set_qty()

        result = mo.button_mark_done()
        # Make sure there's no warning again.
        self.assertIs(result, True, "The quantities the wizard readjusted didn't conform to the BoM.")

        for move in mo.move_raw_ids:
            if move.product_id == self.water:
                self.assertEqual(move.uom_id, self.uom_ml, "The wizard reverted the component UoM.")
                self.assertEqual(move.quantity, 4_000_000, "The wizard failed to correct the consumed quantity.")
            elif move.product_id == self.msg:
                self.assertEqual(move.uom_id, self.uom_kg, "The wizard reverted the component UoM.")
                self.assertEqual(move.quantity, 36, "The wizard failed to correct the consumed quantity.")

    def test_consumption_warning_with_readded_component(self):
        """Check that the consumption warning wizard can match readded
        components with BoM lines that are missing move counterparts."""
        mo = self._make_mo(self.soup_recipe, 5, self.uom_m3)
        mo.action_confirm()

        mo.move_raw_ids.filtered(lambda move: move.product_id in (self.water, self.msg)).unlink()
        self.env['stock.move'].create([
            # Correct product and quantity, but incorrect UoM. This will be considered foreign, given 0 quantity,
            # and a new move will be created to take its place.
            {
                'product_id': self.water.id,
                'uom_id': self.uom_l.id,
                'product_uom_qty': 4000,
                'raw_material_production_id': mo.id,
            },
            # Correct product and UoM, but incorrect quantity. The wizard will correct the quantity for us.
            {
                'product_id': self.msg.id,
                'uom_id': self.uom_g.id,
                'product_uom_qty': 24_000,
                'raw_material_production_id': mo.id,
            },
        ])

        warning = Form.from_action(self.env, mo.button_mark_done()).save()
        self.assertRecordValues(warning.mrp_consumption_warning_line_ids, [
            # Considered foreign.
            {
                'product_id': self.water.id,
                'product_consumed_qty_uom': 4000,
                'product_expected_qty_uom': 0,
                'uom_id': self.uom_l.id,
            },
            # Recognised as belonging to the BoM, just with the wrong quantity.
            {
                'product_id': self.msg.id,
                'product_consumed_qty_uom': 24_000,
                'product_expected_qty_uom': 36_000,
                'uom_id': self.uom_g.id,
            },
            # Still missing.
            {
                'product_id': self.water.id,
                'product_consumed_qty_uom': 0,
                'product_expected_qty_uom': 4,
                'uom_id': self.uom_m3.id,
            },
        ])
        warning.action_set_qty()

        result = mo.button_mark_done()
        # Make sure there's no warning again.
        self.assertIs(result, True, "The wizard failed to make the components conform to the BoM.")

        self.assertEqual(len(mo.move_raw_ids.filtered(lambda move: move.product_id == self.water)), 2,
                         "The final result must contain the (empty) component with the wrong BoM "
                         "and the component with the correct BoM & quantity created by the wizard.")
        for move in mo.move_raw_ids:
            if move.product_id == self.water:
                if move.uom_id == self.uom_l:
                    self.assertEqual(move.quantity, 0,
                                     "We consumed the foreign component with the wrong UoM.")
                else:
                    self.assertEqual(move.uom_id, self.uom_m3,
                                     "Somehow, the move the wizard added back ended up with a completely unrelated UoM.")
                    self.assertEqual(move.quantity, 4,
                                     "The move was readded with the wrong quantity.")
            elif move.product_id == self.msg:
                self.assertEqual(move.uom_id, self.uom_g,
                                 "Somehow, the move we added back ended up with a completely unrelated UoM.")
                self.assertEqual(move.quantity, 36_000,
                                 "The move was readded with the wrong quantity.")
            else:
                self.assertIn(move.product_id, (self.noodles, self.oil, self.salt),
                              "Foreign component in the MO.")

    def test_consumption_warning_no_bom(self):
        """Check that the consumption warning wizard will work even without
        a BoM, using the 'To Consume' quantity as the goal."""
        mo_form = Form(self.env['mrp.production'])
        mo_form.product_id = self.soup
        mo_form.product_qty = 1
        mo_form.uom_id = self.uom_l

        # Reset the BoM and add custom components
        mo_form.bom_id = self.env['mrp.bom']
        with mo_form.move_raw_ids.new() as move:
            move.product_id = self.noodles
            move.uom_id = self.uom_kg
            move.product_uom_qty = 0.25
            move.quantity = 0.2
        with mo_form.move_raw_ids.new() as move:
            move.product_id = self.water
            move.uom_id = self.uom_l
            move.product_uom_qty = 1.2
            move.quantity = 0.8
        with mo_form.move_raw_ids.new() as move:
            move.product_id = self.salt
            move.uom_id = self.uom_g
            move.product_uom_qty = 5

        mo = mo_form.save()
        mo.action_confirm()

        warning = Form.from_action(self.env, mo.button_mark_done()).save()
        self.assertRecordValues(warning.mrp_consumption_warning_line_ids, [
            {
                'product_id': self.noodles.id,
                'uom_id': self.uom_kg.id,
                'product_consumed_qty_uom': 0.2,
                'product_expected_qty_uom': 0.25,
            },
            {
                'product_id': self.water.id,
                'uom_id': self.uom_l.id,
                'product_consumed_qty_uom': 0.8,
                'product_expected_qty_uom': 1.2,
            },
        ])
        warning.action_set_qty()

        result = mo.button_mark_done()
        # Make sure there's no warning again.
        self.assertIs(result, True, "The wizard failed to make the components conform to the BoM.")

        for move in mo.move_raw_ids:
            if move.product_id == self.noodles:
                self.assertEqual(move.quantity, 0.25, "Wrong quantity of the component was consumed.")
            elif move.product_id == self.water:
                self.assertEqual(move.quantity, 1.2, "Wrong quantity of the component was consumed.")
            else:
                self.assertEqual(move.product_id, self.salt, "Foreign component in the MO.")
