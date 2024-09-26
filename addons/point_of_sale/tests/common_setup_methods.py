from odoo.fields import Command


def setup_product_combo_items(self):
    tax10 = self.env["account.tax"].create(
        {
            "name": "10%",
            "amount": 10,
            "amount_type": "percent",
            "type_tax_use": "sale",
        }
    )
    tax20in = self.env["account.tax"].create(
        {
            "name": "20% incl",
            "amount": 20,
            "amount_type": "percent",
            "type_tax_use": "sale",
            "price_include_override": "tax_included",
            "include_base_amount": True,
        }
    )
    tax30 = self.env["account.tax"].create(
        {
            "name": "30%",
            "amount": 30,
            "amount_type": "percent",
            "type_tax_use": "sale",
        }
    )

    combo_product_1 = self.env["product.product"].create(
        {
            "name": "Combo Product 1",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 10,
            "taxes_id": [(6, 0, [tax10.id])],
        }
    )

    combo_product_2 = self.env["product.product"].create(
        {
            "name": "Combo Product 2",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 11,
            "taxes_id": [(6, 0, [tax20in.id])],
        }
    )

    combo_product_3 = self.env["product.product"].create(
        {
            "name": "Combo Product 3",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 16,
            "taxes_id": [(6, 0, [tax30.id])],
        }
    )

    self.desk_accessories_combo = self.env["product.combo"].create(
        {
            "name": "Desk Accessories Combo",
            "combo_item_ids": [
                Command.create({
                    "product_id": combo_product_1.id,
                    "extra_price": 0,
                }),
                Command.create({
                    "product_id": combo_product_2.id,
                    "extra_price": 0,
                }),
                Command.create({
                    "product_id": combo_product_3.id,
                    "extra_price": 2,
                }),
            ],
        }
    )

    combo_product_4 = self.env["product.product"].create(
        {
            "name": "Combo Product 4",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 20,
            "taxes_id": [(6, 0, [tax10.id])],
        }
    )

    combo_product_5 = self.env["product.product"].create(
        {
            "name": "Combo Product 5",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 25,
            "taxes_id": [(6, 0, [tax20in.id])],
        }
    )

    self.desks_combo = self.env["product.combo"].create(
        {
            "name": "Desks Combo",
            "combo_item_ids": [
                Command.create({
                    "product_id": combo_product_4.id,
                    "extra_price": 0,
                }),
                Command.create({
                    "product_id": combo_product_5.id,
                    "extra_price": 2,
                }),
            ],
        }
    )

    combo_product_6 = self.env["product.product"].create(
        {
            "name": "Combo Product 6",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 30,
            "taxes_id": [(6, 0, [tax30.id])],
        }
    )

    combo_product_7 = self.env["product.product"].create(
        {
            "name": "Combo Product 7",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 32,
            "taxes_id": [(6, 0, [tax10.id])],
        }
    )

    combo_product_8 = self.env["product.product"].create(
        {
            "name": "Combo Product 8",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 40,
            "taxes_id": [(6, 0, [tax20in.id])],
        }
    )

    combo_product_9 = self.env["product.product"].create(
        {
            "name": "Combo Product 9",
            "is_storable": True,
            "available_in_pos": True,
            "list_price": 50,
            "taxes_id": [(6, 0, [tax20in.id])],
        }
    )

    chair_color_attribute = self.env['product.attribute'].create({
        'name': 'Color',
        'display_type': 'color',
        'create_variant': 'no_variant',
    })
    chair_color_red = self.env['product.attribute.value'].create({
        'name': 'Red',
        'attribute_id': chair_color_attribute.id,
        'html_color': '#ff0000',
    })
    chair_color_blue = self.env['product.attribute.value'].create({
        'name': 'Blue',
        'attribute_id': chair_color_attribute.id,
        'html_color': '#0000ff',
    })
    self.env['product.template.attribute.line'].create({
        'product_tmpl_id': combo_product_9.product_tmpl_id.id,
        'attribute_id': chair_color_attribute.id,
        'value_ids': [(6, 0, [chair_color_red.id, chair_color_blue.id])]
    })

    color_attribute = self.env['product.attribute'].create({
        'name': 'Color always',
        'sequence': 4,
        'create_variant': 'always',
        'value_ids': [(0, 0, {
            'name': 'White',
            'sequence': 1,
        }), (0, 0, {
            'name': 'Red',
            'sequence': 2,
        })],
    })

    product_10_template = self.env['product.template'].create({
        'name': 'Combo Product 10',
        'list_price': 200,
        'taxes_id': False,
        'available_in_pos': True,
        'attribute_line_ids': [(0, 0, {
            'attribute_id': color_attribute.id,
            'value_ids': [(6, 0, color_attribute.value_ids.ids)]
        })],
    })

    self.chairs_combo = self.env["product.combo"].create(
        {
            "name": "Chairs Combo",
            "combo_item_ids": [
                Command.create({
                    "product_id": combo_product_6.id,
                    "extra_price": 0,
                }),
                Command.create({
                    "product_id": combo_product_7.id,
                    "extra_price": 0,
                }),
                Command.create({
                    "product_id": combo_product_8.id,
                    "extra_price": 5,
                }),
                Command.create({
                    "product_id": combo_product_9.id,
                    "extra_price": 0,
                }),
                Command.create({
                    "product_id": product_10_template.product_variant_ids[0].id,
                    "extra_price": 0,
                }),
                Command.create({
                    "product_id": product_10_template.product_variant_ids[1].id,
                    "extra_price": 0,
                }),
            ],
        }
    )

    # Archive one variant
    product_10_template.product_variant_ids[0].write({'active': False})

    # Create Office Combo
    self.office_combo = self.env["product.product"].create(
        {
            "available_in_pos": True,
            "list_price": 40,
            "name": "Office Combo",
            "type": "combo",
            "categ_id": self.env.ref("product.product_category_1").id,
            "uom_id": self.env.ref("uom.product_uom_unit").id,
            "uom_po_id": self.env.ref("uom.product_uom_unit").id,
            "combo_ids": [
                (6, 0, [self.desks_combo.id, self.chairs_combo.id, self.desk_accessories_combo.id])
            ],
        }
    )
