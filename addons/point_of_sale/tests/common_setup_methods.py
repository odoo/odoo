from odoo.fields import Command

def setup_pos_combo_items(self):
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
            "price_include": True,
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
            "type": "product",
            "available_in_pos": True,
            "list_price": 10,
            "taxes_id": [(6, 0, [tax10.id])],
        }
    )

    combo_product_2 = self.env["product.product"].create(
        {
            "name": "Combo Product 2",
            "type": "product",
            "available_in_pos": True,
            "list_price": 11,
            "taxes_id": [(6, 0, [tax20in.id])],
        }
    )

    combo_product_3 = self.env["product.product"].create(
        {
            "name": "Combo Product 3",
            "type": "product",
            "available_in_pos": True,
            "list_price": 16,
            "taxes_id": [(6, 0, [tax30.id])],
        }
    )

    desk_organizer_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_1.id,
            "combo_price": 0,
        }
    )

    desk_pad_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_2.id,
            "combo_price": 0,
        }
    )

    monitor_stand_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_3.id,
            "combo_price": 2,
        }
    )

    self.desk_accessories_combo = self.env["pos.combo"].create(
        {
            "name": "Desk Accessories Combo",
            "combo_line_ids": [
                (
                    6,
                    0,
                    [
                        desk_organizer_combo_line.id,
                        desk_pad_combo_line.id,
                        monitor_stand_combo_line.id,
                    ],
                )
            ],
        }
    )

    combo_product_4 = self.env["product.product"].create(
        {
            "name": "Combo Product 4",
            "type": "product",
            "available_in_pos": True,
            "list_price": 20,
            "taxes_id": [(6, 0, [tax10.id])],
        }
    )

    combo_product_5 = self.env["product.product"].create(
        {
            "name": "Combo Product 5",
            "type": "product",
            "available_in_pos": True,
            "list_price": 25,
            "taxes_id": [(6, 0, [tax20in.id])],
        }
    )

    product_4_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_4.id,
            "combo_price": 0,
        }
    )

    product_5_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_5.id,
            "combo_price": 2,
        }
    )

    self.desks_combo = self.env["pos.combo"].create(
        {
            "name": "Desks Combo",
            "combo_line_ids": [
                (6, 0, [product_4_combo_line.id, product_5_combo_line.id])
            ],
        }
    )

    combo_product_6 = self.env["product.product"].create(
        {
            "name": "Combo Product 6",
            "type": "product",
            "available_in_pos": True,
            "list_price": 30,
            "taxes_id": [(6, 0, [tax30.id])],
        }
    )

    combo_product_7 = self.env["product.product"].create(
        {
            "name": "Combo Product 7",
            "type": "product",
            "available_in_pos": True,
            "list_price": 32,
            "taxes_id": [(6, 0, [tax10.id])],
        }
    )

    combo_product_8 = self.env["product.product"].create(
        {
            "name": "Combo Product 8",
            "type": "product",
            "available_in_pos": True,
            "list_price": 40,
            "taxes_id": [(6, 0, [tax20in.id])],
        }
    )

    combo_product_9 = self.env["product.product"].create(
        {
            "name": "Combo Product 9",
            "type": "product",
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

    product_6_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_6.id,
            "combo_price": 0,
        }
    )

    product_7_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_7.id,
            "combo_price": 0,
        }
    )

    product_8_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_8.id,
            "combo_price": 5,
        }
    )

    product_9_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": combo_product_9.id,
            "combo_price": 5,
        }
    )

    self.chairs_combo = self.env["pos.combo"].create(
        {
            "name": "Chairs Combo",
            "combo_line_ids": [
                (
                    6,
                    0,
                    [
                        product_6_combo_line.id,
                        product_7_combo_line.id,
                        product_8_combo_line.id,
                        product_9_combo_line.id,
                    ],
                )
            ],
        }
    )

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

    #Create Combo with custom attribute
    custom_attribute = self.env['product.attribute'].create({
        'name': 'Custom Attribute',
        'display_type': 'radio',
        'create_variant': 'no_variant',
        'value_ids': [
                Command.create({'name': 'Custom Value', 'is_custom': True}),
        ]
    })

    self.product_tmpl_with_custom_attr = self.env["product.template"].create(
        {
            "name": "Custom Attr Product",
            "available_in_pos": True,
            "attribute_line_ids": [
                Command.create({
                    'attribute_id': custom_attribute.id,
                    'value_ids': [Command.set(custom_attribute.value_ids.ids)],
                })
            ],
        }
    )

    custom_combo_line = self.env["pos.combo.line"].create(
        {
            "product_id": self.product_tmpl_with_custom_attr.product_variant_id.id,
            "combo_price": 100,
        }
    )

    custom_combo = self.env["pos.combo"].create({
        "name": "Attr Combo",
        "combo_line_ids": custom_combo_line.ids,
    })

    self.combo_product_with_custom_attr = self.env["product.product"].create(
        {
            "available_in_pos": True,
            "list_price": 40,
            "name": "Custom Attr Combo",
            "type": "combo",
            "combo_ids": custom_combo.ids,
        }
    )
