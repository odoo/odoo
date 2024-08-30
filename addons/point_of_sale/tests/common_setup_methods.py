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
