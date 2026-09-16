from datetime import timedelta

from odoo import exceptions, fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import Form, HttpCase, freeze_time, tagged
from odoo.tools import float_compare, float_repr, float_round

from odoo.addons.mrp.tests.common import TestMrpCommon


@freeze_time(fields.Date.today())
class TestBoM(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_user.write(
            {
                "implied_ids": [
                    Command.link(cls.group_product_variant.id),
                    Command.link(cls.group_mrp_routings.id),
                ]
            }
        )

    @classmethod
    def make_prods(cls, n):
        return cls.env["product.product"].create(
            [{"name": f"p{k + 1}", "is_storable": True} for k in range(n)]
        )

    @classmethod
    def _get_component_line(cls, bom, product, qty=1.0):
        data = cls.env["report.mrp.report_bom_structure"]._get_report_data(
            bom.id, searchQty=qty
        )["lines"]
        return next(c for c in data["components"] if c["product_id"] == product.id)

    def test_01_explode(self):
        boms, lines = self.bom_1._explode(self.product_4, 3)
        self.assertEqual({bom[0].id for bom in boms}, set(self.bom_1.ids))
        self.assertEqual(
            {line[0].id for line in lines}, set(self.bom_1.bom_line_ids.ids)
        )

        boms, lines = self.bom_3._explode(self.product_6, 3)
        self.assertEqual(
            {bom[0].id for bom in boms}, set((self.bom_2 | self.bom_3).ids)
        )
        self.assertEqual(
            {line[0].id for line in lines},
            set(
                (self.bom_2 | self.bom_3)
                .mapped("bom_line_ids")
                .filtered(
                    lambda line: (
                        not line.child_bom_id or line.child_bom_id.type != "phantom"
                    )
                )
                .ids
            ),
        )

    def test_02_explode_rounding(self):
        fns, cmp1, cmp2 = self.env["product.product"].create(
            [{"name": "FNS"}, {"name": "CMP1"}, {"name": "CMP2"}]
        )
        self.uom_unit.rounding = 0.01

        fns_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": fns.product_tmpl_id.id,
                "product_qty": 1,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create({"product_id": cmp1.id, "product_qty": 10})
                ],
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": cmp1.product_tmpl_id.id,
                "product_qty": 5000,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create({"product_id": cmp2.id, "product_qty": 50})
                ],
            }
        )

        _, lines = fns_bom._explode(fns, 1)
        self.assertEqual(lines[0][1]["qty"], 0.10)

    def test_10_variants(self):
        test_bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 4.0,
                "type": "normal",
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Cutting Machine",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 12,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Weld Machine",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 18,
                            "sequence": 2,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(self.product_7_attr1_v1.id)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "Taking a coffee",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 5,
                            "sequence": 3,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(self.product_7_attr1_v2.id)
                            ],
                        }
                    ),
                ],
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "product_uom_id": self.product_1.uom_id.id,
                            "product_qty": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_uom_id": self.product_2.uom_id.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(self.product_7_attr1_v1.id)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_uom_id": self.product_3.uom_id.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(self.product_7_attr1_v2.id)
                            ],
                        }
                    ),
                ],
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 2,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_qty": 2,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(self.product_7_attr1_v1.id)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_4.id,
                            "product_qty": 2,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(self.product_7_attr1_v2.id)
                            ],
                        }
                    ),
                ],
            }
        )
        test_bom_l1, test_bom_l2, test_bom_l3 = test_bom.bom_line_ids
        boms, lines = test_bom._explode(self.product_7_3, 4)
        self.assertIn(test_bom, [b[0] for b in boms])
        self.assertIn(test_bom_l1, [l[0] for l in lines])
        self.assertNotIn(test_bom_l2, [l[0] for l in lines])
        self.assertNotIn(test_bom_l3, [l[0] for l in lines])

        boms, lines = test_bom._explode(self.product_7_1, 4)
        self.assertIn(test_bom, [b[0] for b in boms])
        self.assertIn(test_bom_l1, [l[0] for l in lines])
        self.assertIn(test_bom_l2, [l[0] for l in lines])
        self.assertNotIn(test_bom_l3, [l[0] for l in lines])

        boms, lines = test_bom._explode(self.product_7_2, 4)
        self.assertIn(test_bom, [b[0] for b in boms])
        self.assertIn(test_bom_l1, [l[0] for l in lines])
        self.assertNotIn(test_bom_l2, [l[0] for l in lines])
        self.assertIn(test_bom_l3, [l[0] for l in lines])

        mrp_order_form = Form(self.env["mrp.production"])
        mrp_order_form.product_id = self.product_7_3
        mrp_order = mrp_order_form.save()
        self.assertEqual(mrp_order.bom_id, test_bom)
        self.assertEqual(len(mrp_order.workorder_ids), 1)
        self.assertEqual(
            mrp_order.workorder_ids.operation_id, test_bom.operation_ids[0]
        )
        self.assertEqual(len(mrp_order.move_byproduct_ids), 1)
        self.assertEqual(mrp_order.move_byproduct_ids.product_id, self.product_1)

        mrp_order_form = Form(self.env["mrp.production"])
        mrp_order_form.product_id = self.product_7_1
        mrp_order_form.product_id = self.env["product.product"]
        mrp_order_form.product_id = self.product_7_1
        mrp_order_form.bom_id = self.env["mrp.bom"]
        mrp_order_form.bom_id = test_bom
        mrp_order = mrp_order_form.save()
        self.assertEqual(mrp_order.bom_id, test_bom)
        self.assertEqual(len(mrp_order.workorder_ids), 2)
        self.assertEqual(
            mrp_order.workorder_ids.operation_id, test_bom.operation_ids[:2]
        )
        self.assertEqual(len(mrp_order.move_byproduct_ids), 2)
        self.assertEqual(
            mrp_order.move_byproduct_ids.product_id, self.product_1 | self.product_2
        )

        mrp_order_form = Form(self.env["mrp.production"])
        mrp_order_form.product_id = self.product_7_2
        mrp_order = mrp_order_form.save()
        self.assertEqual(mrp_order.bom_id, test_bom)
        self.assertEqual(len(mrp_order.workorder_ids), 2)
        self.assertEqual(
            mrp_order.workorder_ids.operation_id,
            test_bom.operation_ids[0] | test_bom.operation_ids[2],
        )
        self.assertEqual(len(mrp_order.move_byproduct_ids), 2)
        self.assertEqual(
            mrp_order.move_byproduct_ids.product_id, self.product_1 | self.product_3
        )

    def test_11_multi_level_variants(self):
        tmp_picking_type = self.env["stock.picking.type"].create(
            {
                "name": "Manufacturing",
                "code": "mrp_operation",
                "sequence_code": "TMP",
                "sequence_id": self.env["ir.sequence"]
                .create(
                    {
                        "code": "mrp.production",
                        "name": "tmp_production_sequence",
                    }
                )
                .id,
            }
        )
        test_bom_1 = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_5.product_tmpl_id.id,
                "product_uom_id": self.product_5.uom_id.id,
                "product_qty": 1.0,
                "type": "phantom",
            }
        )
        test_bom_1.write(
            {
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Gift Wrap Maching",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 15,
                            "sequence": 1,
                        }
                    )
                ]
            }
        )
        test_bom_1.bom_line_ids = [
            Command.create(
                {
                    "product_id": self.product_3.id,
                    "product_qty": 3,
                }
            )
        ]

        test_bom_2 = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 4.0,
                "type": "normal",
            }
        )
        test_bom_2.write(
            {
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Cutting Machine",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 12,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Weld Machine",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 18,
                            "sequence": 2,
                        }
                    ),
                ]
            }
        )
        test_bom_2.bom_line_ids = [
            Command.create(
                {
                    "product_id": self.product_2.id,
                    "product_qty": 2,
                }
            )
        ]
        test_bom_2.bom_line_ids = [
            Command.create(
                {
                    "product_id": self.product_5.id,
                    "product_qty": 2,
                    "bom_product_template_attribute_value_ids": [
                        Command.link(self.product_7_attr1_v1.id)
                    ],
                }
            )
        ]
        test_bom_2.bom_line_ids = [
            Command.create(
                {
                    "product_id": self.product_5.id,
                    "product_qty": 2,
                    "bom_product_template_attribute_value_ids": [
                        Command.link(self.product_7_attr1_v2.id)
                    ],
                }
            )
        ]
        test_bom_2.bom_line_ids = [
            Command.create(
                {
                    "product_id": self.product_4.id,
                    "product_qty": 2,
                }
            )
        ]
        test_bom_2_l1, _test_bom_2_l2, _test_bom_2_l3, test_bom_2_l4 = (
            test_bom_2.bom_line_ids
        )

        boms, lines = test_bom_2._explode(self.product_7_1, 4)
        self.assertEqual(set((test_bom_2 | self.bom_2).ids), {b[0].id for b in boms})
        self.assertEqual(
            set((test_bom_2_l1 | test_bom_2_l4 | self.bom_2.bom_line_ids).ids),
            {l[0].id for l in lines},
        )

        test_bom_1.write({"sequence": 1})
        boms, lines = test_bom_2._explode(self.product_7_1, 4)
        self.assertEqual(set((test_bom_2 | test_bom_1).ids), {b[0].id for b in boms})
        self.assertEqual(
            set((test_bom_2_l1 | test_bom_2_l4 | test_bom_1.bom_line_ids).ids),
            {l[0].id for l in lines},
        )

        test_bom_1.write({"picking_type_id": self.picking_type_manu.id})
        self.bom_2.write({"picking_type_id": tmp_picking_type.id})
        test_bom_2.write({"picking_type_id": tmp_picking_type.id})
        boms, lines = test_bom_2._explode(self.product_7_1, 4)
        self.assertEqual(set((test_bom_2 | self.bom_2).ids), {b[0].id for b in boms})
        self.assertEqual(
            set((test_bom_2_l1 | test_bom_2_l4 | self.bom_2.bom_line_ids).ids),
            {l[0].id for l in lines},
        )

        self.product_9, self.product_10 = self.env["product.product"].create(
            [
                {
                    "name": "Paper",
                },
                {
                    "name": "Stone",
                },
            ]
        )

        test_bom_3 = self.env["mrp.bom"].create(
            {
                "product_id": self.product_9.id,
                "product_tmpl_id": self.product_9.product_tmpl_id.id,
                "product_uom_id": self.product_9.uom_id.id,
                "product_qty": 1.0,
                "consumption": "flexible",
                "type": "normal",
            }
        )
        test_bom_4 = self.env["mrp.bom"].create(
            {
                "product_id": self.product_10.id,
                "product_tmpl_id": self.product_10.product_tmpl_id.id,
                "product_uom_id": self.product_10.uom_id.id,
                "product_qty": 1.0,
                "consumption": "flexible",
                "type": "phantom",
            }
        )
        test_bom_3.bom_line_ids = [
            Command.create(
                {
                    "product_id": self.product_10.id,
                    "product_qty": 1.0,
                }
            )
        ]
        with self.assertRaises(exceptions.UserError):
            test_bom_4.bom_line_ids = [
                Command.create(
                    {
                        "product_id": self.product_9.id,
                        "product_qty": 1.0,
                    }
                )
            ]

    def test_12_multi_level_variants2(self):

        Product = self.env["product.product"]
        ProductAttribute = self.env["product.attribute"]
        ProductAttributeValue = self.env["product.attribute.value"]

        att_color = ProductAttribute.create({"name": "Color", "sequence": 1})
        att_size = ProductAttribute.create({"name": "size", "sequence": 2})

        att_color_red = ProductAttributeValue.create(
            {"name": "red", "attribute_id": att_color.id, "sequence": 1}
        )
        att_color_blue = ProductAttributeValue.create(
            {"name": "blue", "attribute_id": att_color.id, "sequence": 2}
        )
        att_size_big = ProductAttributeValue.create(
            {"name": "big", "attribute_id": att_size.id, "sequence": 1}
        )
        att_size_medium = ProductAttributeValue.create(
            {"name": "medium", "attribute_id": att_size.id, "sequence": 2}
        )

        product_template = self.env["product.template"].create(
            {
                "name": "Sofa",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": att_color.id,
                            "value_ids": [
                                (6, 0, [att_color_red.id, att_color_blue.id])
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "attribute_id": att_size.id,
                            "value_ids": [
                                (6, 0, [att_size_big.id, att_size_medium.id])
                            ],
                        }
                    ),
                ],
            }
        )

        sofa_red = product_template.attribute_line_ids[0].product_template_value_ids[0]
        sofa_blue = product_template.attribute_line_ids[0].product_template_value_ids[1]

        sofa_big = product_template.attribute_line_ids[1].product_template_value_ids[0]
        sofa_medium = product_template.attribute_line_ids[1].product_template_value_ids[
            1
        ]

        product_A = Product.create({"name": "Wood"})
        product_B = Product.create({"name": "Clothes"})

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": product_A.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(sofa_red.id),
                                Command.link(sofa_blue.id),
                                Command.link(sofa_big.id),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": product_B.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(sofa_red.id),
                                Command.link(sofa_blue.id),
                            ],
                        }
                    ),
                ],
            }
        )

        dict_consumed_products = {
            sofa_red + sofa_big: product_A + product_B,
            sofa_red + sofa_medium: product_B,
            sofa_blue + sofa_big: product_A + product_B,
            sofa_blue + sofa_medium: product_B,
        }

        for combination, consumed_products in dict_consumed_products.items():
            product = product_template.product_variant_ids.filtered(
                lambda p, combination=combination: (
                    p.product_template_attribute_value_ids == combination
                )
            )
            mrp_order_form = Form(self.env["mrp.production"])
            mrp_order_form.product_id = product
            mrp_order = mrp_order_form.save()

            self.assertEqual(mrp_order.move_raw_ids.product_id, consumed_products)

    def test_13_bom_kit_qty(self):
        self.env["mrp.bom"].create(
            {
                "product_id": self.product_7_3.id,
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 4.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 2,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_qty": 2,
                        }
                    ),
                ],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_2, self.stock_location, 4.0
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_3, self.stock_location, 8.0
        )
        kit_product_qty, _, _ = (
            self.product_7_3 + self.product_2 + self.product_3
        ).mapped("qty_available")
        self.assertEqual(kit_product_qty, 8)

    def test_kit_quantity_search(self):
        self.env["mrp.bom"].create(
            {
                "product_id": self.product_7_3.id,
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create({"product_id": self.product_2.id, "product_qty": 3}),
                ],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            self.product_2, self.stock_location, 12.0
        )
        self.assertEqual(self.product_7_3.qty_available_virtual, 4.0)
        found = self.env["product.product"].search(
            ["&", ("id", "in", self.product_7_3.ids), ("qty_available_virtual", ">", 0)]
        )
        self.assertEqual(
            found,
            self.product_7_3,
            "kit must be found by a qty_available_virtual search",
        )
        excluded = self.env["product.product"].search(
            [
                "&",
                ("id", "in", self.product_7_3.ids),
                ("qty_available_virtual", ">", 10),
            ]
        )
        self.assertFalse(
            excluded, "kit must be excluded when its quantity fails the operator"
        )

    def test_14_bom_kit_qty_multi_uom(self):
        product_unit = self.env["product.product"].create(
            {
                "name": "Test units",
                "type": "consu",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        product_dozens = self.env["product.product"].create(
            {
                "name": "Test dozens",
                "type": "consu",
                "is_storable": True,
                "uom_id": self.uom_dozen.id,
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_unit.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": product_dozens.id,
                            "product_qty": 1,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                ],
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product_dozens, self.stock_location, 1.0
        )
        self.assertEqual(product_unit.qty_available, 12.0)

    def test_13_negative_on_hand_qty(self):
        precision = self.env.ref("uom.decimal_product_uom")
        precision.digits = 5

        _ = self.env["mrp.bom"].create(
            {
                "product_id": self.product_2.id,
                "product_tmpl_id": self.product_2.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.00,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_qty": 1.000,
                        }
                    ),
                ],
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            self.product_3, self.stock_location, -384.0
        )

        kit_product_qty = self.product_2.qty_available
        self.assertEqual(
            float_repr(
                float_round(kit_product_qty, precision_digits=precision.digits),
                precision_digits=precision.digits,
            ),
            "-384.00000",
        )

        self.product_2.invalidate_recordset(["qty_available"])
        kit_product_qty, _ = (self.product_2 + self.product_3).mapped("qty_available")
        self.assertEqual(
            float_repr(
                float_round(kit_product_qty, precision_digits=precision.digits),
                precision_digits=precision.digits,
            ),
            "-384.00000",
        )

    def test_19_bom_kit_field_is_kit_bom_with_product_id(self):
        kit_products = self.env["product.product"].create(
            {
                "name": "No Kit",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_id": kit_products.id,
                "product_tmpl_id": kit_products.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 4.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 2,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_qty": 2,
                        }
                    ),
                ],
            }
        )
        self.assertTrue(kit_products.is_kit)
        self.assertTrue(kit_products.product_tmpl_id.is_kit)

        no_kit_products = self.env["product.product"].create(
            {
                "name": "No Kit",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        self.assertFalse(no_kit_products.is_kit)
        self.assertFalse(no_kit_products.product_tmpl_id.is_kit)

        product_with_kit = self.env["product.product"].search([("is_kit", "=", True)])
        product_tmpl_with_kit = self.env["product.template"].search(
            [("is_kit", "=", True)]
        )
        self.assertIn(kit_products, product_with_kit)
        self.assertIn(kit_products.product_tmpl_id, product_tmpl_with_kit)
        self.assertNotIn(no_kit_products, product_with_kit)
        self.assertNotIn(no_kit_products.product_tmpl_id, product_tmpl_with_kit)

        product_without_kit = self.env["product.product"].search(
            [("is_kit", "=", False)]
        )
        product_tmpl_without_kit = self.env["product.template"].search(
            [("is_kit", "=", False)]
        )
        self.assertIn(no_kit_products, product_without_kit)
        self.assertIn(no_kit_products.product_tmpl_id, product_tmpl_without_kit)
        self.assertNotIn(kit_products, product_without_kit)
        self.assertNotIn(kit_products.product_tmpl_id, product_tmpl_without_kit)

    def test_19_bom_kit_field_is_kit_bom_without_product_id(self):
        kit_products = self.env["product.product"].create(
            {
                "name": "No Kit",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": kit_products.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 4.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 2,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_qty": 2,
                        }
                    ),
                ],
            }
        )
        self.assertTrue(kit_products.is_kit)
        self.assertTrue(kit_products.product_tmpl_id.is_kit)

        no_kit_products = self.env["product.product"].create(
            {
                "name": "No Kit",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        self.assertFalse(no_kit_products.is_kit)
        self.assertFalse(no_kit_products.product_tmpl_id.is_kit)

        product_with_kit = self.env["product.product"].search([("is_kit", "=", True)])
        product_tmpl_with_kit = self.env["product.template"].search(
            [("is_kit", "=", True)]
        )
        self.assertIn(kit_products, product_with_kit)
        self.assertIn(kit_products.product_tmpl_id, product_tmpl_with_kit)
        self.assertNotIn(no_kit_products, product_with_kit)
        self.assertNotIn(no_kit_products.product_tmpl_id, product_tmpl_with_kit)

        product_without_kit = self.env["product.product"].search(
            [("is_kit", "=", False)]
        )
        product_tmpl_without_kit = self.env["product.template"].search(
            [("is_kit", "=", False)]
        )
        self.assertIn(no_kit_products, product_without_kit)
        self.assertIn(no_kit_products.product_tmpl_id, product_tmpl_without_kit)
        self.assertNotIn(kit_products, product_without_kit)
        self.assertNotIn(kit_products.product_tmpl_id, product_tmpl_without_kit)

    def test_20_bom_report(self):
        uom_kg = self.env.ref("uom.product_uom_kgm")
        uom_litre = self.env.ref("uom.product_uom_litre")
        crumble = self.env["product.product"].create(
            {
                "name": "Crumble",
                "is_storable": True,
                "uom_id": uom_kg.id,
            }
        )
        butter = self.env["product.product"].create(
            {
                "name": "Butter",
                "is_storable": True,
                "uom_id": uom_kg.id,
                "standard_price": 7.01,
            }
        )
        biscuit = self.env["product.product"].create(
            {
                "name": "Biscuit",
                "is_storable": True,
                "uom_id": uom_kg.id,
                "standard_price": 1.5,
            }
        )
        bom_form_crumble = Form(self.env["mrp.bom"])
        bom_form_crumble.product_tmpl_id = crumble.product_tmpl_id
        bom_form_crumble.product_qty = 11
        bom_form_crumble.product_uom_id = uom_kg
        bom_crumble = bom_form_crumble.save()

        workcenter = self.env["mrp.workcenter"].create(
            {"costs_hour": 10, "name": "Deserts Table"}
        )

        bom_crumble.write(
            {
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": butter.id,
                            "product_uom_id": uom_kg.id,
                            "product_qty": 5,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": biscuit.id,
                            "product_uom_id": uom_kg.id,
                            "product_qty": 6,
                        }
                    ),
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "workcenter_id": workcenter.id,
                            "name": "Prepare biscuits",
                            "time_cycle_manual": 5 * bom_crumble.product_qty,
                        }
                    ),
                    Command.create(
                        {
                            "workcenter_id": workcenter.id,
                            "name": "Prepare butter",
                            "time_cycle_manual": 3 * bom_crumble.product_qty,
                        }
                    ),
                    Command.create(
                        {
                            "workcenter_id": workcenter.id,
                            "name": "Mix manually",
                            "time_cycle_manual": 5 * bom_crumble.product_qty,
                        }
                    ),
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_crumble.id, searchQty=11, searchVariant=False
        )
        self.assertEqual(
            report_values["lines"]["operations_time"],
            143.0,
            "Operation time should be the same for 1 unit or for the batch",
        )
        self.assertEqual(
            float_compare(
                report_values["lines"]["operations_cost"], 23.84, precision_digits=2
            ),
            0,
            "143 minute for 10$/hours -> 23.84",
        )

        for component_line in report_values["lines"]["components"]:
            if component_line["product"].id == butter.id:
                self.assertEqual(
                    float_compare(
                        component_line["bom_cost"], (7.01 * 5), precision_digits=2
                    ),
                    0,
                )
            if component_line["product"].id == biscuit.id:
                self.assertEqual(
                    float_compare(
                        component_line["bom_cost"], (1.5 * 6), precision_digits=2
                    ),
                    0,
                )
        self.assertEqual(
            float_compare(
                report_values["lines"]["bom_cost"], 67.89, precision_digits=2
            ),
            0,
            "Product Bom Price is not correct",
        )
        self.assertEqual(
            float_compare(
                report_values["lines"]["bom_cost"] / 11.0, 6.17, precision_digits=2
            ),
            0,
            "Product Unit Bom Price is not correct",
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_crumble.id, searchQty=1, searchVariant=False
        )
        self.assertEqual(
            report_values["lines"]["operations_time"],
            143.0,
            "Operation time should be the same for 1 unit or for the batch",
        )
        operation_cost = float_round(
            bom_crumble.product_qty * 5 / 60 * 10, precision_digits=2
        ) * 2 + float_round(bom_crumble.product_qty * 3 / 60 * 10, precision_digits=2)
        self.assertEqual(
            float_compare(
                report_values["lines"]["operations_cost"],
                operation_cost,
                precision_digits=2,
            ),
            0,
            "13 minute for 10$/hours -> 2.16",
        )

        for component_line in report_values["lines"]["components"]:
            if component_line["product"].id == butter.id:
                self.assertEqual(
                    float_compare(
                        component_line["bom_cost"],
                        (7.01 * 5) * (1 / 11),
                        precision_digits=2,
                    ),
                    0,
                )
            if component_line["product"].id == biscuit.id:
                self.assertEqual(
                    float_compare(
                        component_line["bom_cost"],
                        (1.5 * 6) * (1 / 11),
                        precision_digits=2,
                    ),
                    0,
                )
        self.assertEqual(
            float_compare(
                report_values["lines"]["bom_cost"], 27.85, precision_digits=2
            ),
            0,
            "Bom Price is not correct",
        )

        self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_crumble.id, searchQty=12, searchVariant=False
        )
        report_values_22 = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_crumble.id, searchQty=22, searchVariant=False
        )

        self.assertEqual(
            float_compare(
                report_values_22["lines"]["operations_cost"], 47.66, precision_digits=2
            ),
            0,
            "Operation cost is not correct",
        )

        cheese_cake = self.env["product.product"].create(
            {
                "name": "Cheese Cake 300g",
                "is_storable": True,
            }
        )
        cream = self.env["product.product"].create(
            {
                "name": "cream",
                "is_storable": True,
                "uom_id": uom_litre.id,
                "standard_price": 5.17,
            }
        )
        bom_form_cheese_cake = Form(self.env["mrp.bom"])
        bom_form_cheese_cake.product_tmpl_id = cheese_cake.product_tmpl_id
        bom_form_cheese_cake.product_qty = 60
        bom_form_cheese_cake.product_uom_id = self.uom_unit
        bom_cheese_cake = bom_form_cheese_cake.save()

        workcenter_2 = self.env["mrp.workcenter"].create(
            {
                "name": "cake mounting",
                "costs_hour": 20,
                "time_start": 10,
                "time_stop": 15,
            }
        )

        self.env["mrp.workcenter.capacity"].create(
            {
                "workcenter_id": workcenter_2.id,
                "product_id": cheese_cake.id,
                "product_uom_id": cheese_cake.uom_id.id,
                "capacity": bom_cheese_cake.product_qty,
                "time_start": 12,
                "time_stop": 16,
            }
        )

        bom_cheese_cake.write(
            {
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": cream.id,
                            "product_uom_id": uom_litre.id,
                            "product_qty": 3,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": crumble.id,
                            "product_uom_id": uom_kg.id,
                            "product_qty": 5.4,
                        }
                    ),
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "workcenter_id": workcenter.id,
                            "name": "Mix cheese and crumble",
                            "time_cycle_manual": 10 * bom_cheese_cake.product_qty,
                        }
                    ),
                    Command.create(
                        {
                            "workcenter_id": workcenter_2.id,
                            "name": "Cake mounting",
                            "time_cycle_manual": 5 * bom_cheese_cake.product_qty,
                        }
                    ),
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_cheese_cake.id, searchQty=60, searchVariant=False
        )
        self.assertEqual(
            report_values["lines"]["operations_time"],
            928.0,
            "Operation time should be the same for 1 unit or for the batch",
        )
        self.assertEqual(
            float_compare(
                report_values["lines"]["operations_cost"], 209.33, precision_digits=2
            ),
            0,
        )

        for component_line in report_values["lines"]["components"]:
            if component_line["product"].id == cream.id:
                self.assertEqual(
                    float_compare(
                        component_line["bom_cost"], (3 * 5.17), precision_digits=2
                    ),
                    0,
                )
            if component_line["product"].id == crumble.id:
                crumble_cost = self.env[
                    "report.mrp.report_bom_structure"
                ]._get_report_data(
                    bom_id=bom_crumble.id, searchQty=5.4, searchVariant=False
                )["lines"]["bom_cost"]
                self.assertEqual(
                    float_compare(
                        component_line["bom_cost"], crumble_cost, precision_digits=2
                    ),
                    0,
                )
        self.assertEqual(
            float_compare(
                report_values["lines"]["bom_cost"], 270.31, precision_digits=2
            ),
            0,
            "Product Bom Price is not correct",
        )

    def test_bom_report_dozens(self):
        drawer = self.env["product.product"].create(
            {
                "name": "drawer",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        screw = self.env["product.product"].create(
            {
                "name": "screw",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
                "standard_price": 7.01,
            }
        )

        bom_form_drawer = Form(self.env["mrp.bom"])
        bom_form_drawer.product_tmpl_id = drawer.product_tmpl_id
        bom_form_drawer.product_qty = 11
        bom_form_drawer.product_uom_id = self.uom_dozen
        bom_drawer = bom_form_drawer.save()

        workcenter = self.env["mrp.workcenter"].create(
            {"costs_hour": 10, "name": "Deserts Table"}
        )
        self.env["mrp.workcenter.capacity"].create(
            {
                "workcenter_id": workcenter.id,
                "product_id": drawer.id,
                "product_uom_id": drawer.uom_id.id,
                "capacity": bom_drawer.product_qty,
            }
        )
        bom_drawer.write(
            {
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": screw.id,
                            "product_uom_id": self.uom_unit.id,
                            "product_qty": 5,
                        }
                    )
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "workcenter_id": workcenter.id,
                            "name": "Screw drawer",
                            "time_cycle_manual": 5 * bom_drawer.product_qty,
                        }
                    )
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_drawer.id, searchQty=11, searchVariant=False
        )
        self.assertEqual(
            report_values["lines"]["operations_time"],
            660.0,
            "Operation time should be the same for 1 unit or for the batch",
        )

    def test_bom_report_planning_with_producible_qty(self):
        self.full_availability()

        location = self.env.ref("stock.stock_location_stock")
        pickaxe = self.env["product.product"].create(
            {
                "name": "Iron Pickaxe",
                "is_storable": True,
                "route_ids": [(6, 0, [self.ref("mrp.route_warehouse0_manufacture")])],
            }
        )
        stick = self.env["product.product"].create(
            {
                "name": "Stick",
                "is_storable": True,
            }
        )
        iron = self.env["product.product"].create(
            {
                "name": "Iron Ingot",
                "is_storable": True,
            }
        )

        bom_form_pickaxe = Form(self.env["mrp.bom"])
        bom_form_pickaxe.product_tmpl_id = pickaxe.product_tmpl_id
        bom_form_pickaxe.product_qty = 1
        bom_pickaxe = bom_form_pickaxe.save()

        workcenter = self.env["mrp.workcenter"].create(
            {"costs_hour": 10, "name": "Crafting Table"}
        )

        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        bom_pickaxe.write(
            {
                "bom_line_ids": [
                    Command.create({"product_id": stick.id, "product_qty": 2}),
                    Command.create({"product_id": iron.id, "product_qty": 3}),
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "workcenter_id": workcenter.id,
                            "name": "Place items",
                            "time_cycle_manual": 10,
                        }
                    ),
                    Command.create(
                        {
                            "workcenter_id": workcenter.id,
                            "name": "Craft items",
                            "time_cycle_manual": 5,
                        }
                    ),
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_pickaxe.id, searchQty=1, searchVariant=False
        )
        self.assertEqual(report_values["lines"]["operations_time"], 15.0)
        self.assertEqual(report_values["lines"]["producible_qty"], 0)

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_pickaxe.id, searchQty=2, searchVariant=False
        )
        self.assertEqual(report_values["lines"]["operations_time"], 30.0)
        self.assertEqual(report_values["lines"]["producible_qty"], 0)

        self.env["ir.config_parameter"].sudo().set_param(
            "mrp.workcenter_max_planning_iterations", "2"
        )
        date_start = fields.Datetime.today() + timedelta(days=14 * 2 - 1)
        end_of_day = date_start + timedelta(days=1)

        self.env["resource.reservation"].create(
            {
                "name": "Game update",
                "date_start": fields.Date.today(),
                "date_end": end_of_day - timedelta(minutes=15),
                "resource_id": workcenter.resource_id.id,
                "allocated_percentage": 100.0,
                "enforcement_mode": "hard",
            }
        )

        self.assertEqual(
            workcenter._get_first_available_slot(date_start, 15),
            (end_of_day - timedelta(minutes=15), end_of_day),
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_pickaxe.id, searchQty=1, searchVariant=False
        )
        self.assertEqual(report_values["lines"]["operations_time"], 15.0)
        self.assertEqual(report_values["lines"]["producible_qty"], 0)

        with self.assertRaises(exceptions.UserError):
            report_values = self.env[
                "report.mrp.report_bom_structure"
            ]._get_report_data(bom_id=bom_pickaxe.id, searchQty=2, searchVariant=False)
            self.assertEqual(report_values["lines"]["operations_time"], 15.0)
            self.assertEqual(report_values["lines"]["producible_qty"], 0)

        self.env["stock.quant"]._update_available_quantity(stick, location, 2.0)
        self.env["stock.quant"]._update_available_quantity(iron, location, 3.0)
        (stick | iron).invalidate_recordset(["qty_free"])
        self.assertEqual(stick.qty_free, 2)
        self.assertEqual(iron.qty_free, 3)

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_pickaxe.id, searchQty=1, searchVariant=False
        )
        self.assertEqual(report_values["lines"]["operations_time"], 15.0)
        self.assertEqual(report_values["lines"]["producible_qty"], 1)

        self.env["stock.quant"]._update_available_quantity(stick, location, 2.0)
        self.env["stock.quant"]._update_available_quantity(iron, location, 3.0)
        (stick | iron).invalidate_recordset(["qty_free"])
        self.assertEqual(stick.qty_free, 4)
        self.assertEqual(iron.qty_free, 6)

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_pickaxe.id, searchQty=1, searchVariant=False
        )
        self.assertEqual(report_values["lines"]["operations_time"], 15.0)
        self.assertEqual(report_values["lines"]["producible_qty"], 2)

        with self.assertRaises(exceptions.UserError):
            report_values = self.env[
                "report.mrp.report_bom_structure"
            ]._get_report_data(bom_id=bom_pickaxe.id, searchQty=2, searchVariant=False)
            self.assertEqual(report_values["lines"]["operations_time"], 15.0)
            self.assertEqual(report_values["lines"]["producible_qty"], 2)

    def test_21_bom_report_variant(self):
        self.car = self.env["product.template"].create(
            {
                "name": "Car",
            }
        )
        self.gps_attribute = self.env["product.attribute"].create(
            {"name": "GPS", "sequence": 1}
        )
        self.gps_yes = self.env["product.attribute.value"].create(
            {
                "name": "Yes",
                "attribute_id": self.gps_attribute.id,
                "sequence": 1,
            }
        )
        self.gps_no = self.env["product.attribute.value"].create(
            {
                "name": "No",
                "attribute_id": self.gps_attribute.id,
                "sequence": 2,
            }
        )

        self.car_gps_attribute_line = self.env[
            "product.template.attribute.line"
        ].create(
            {
                "product_tmpl_id": self.car.id,
                "attribute_id": self.gps_attribute.id,
                "value_ids": [(6, 0, [self.gps_yes.id, self.gps_no.id])],
            }
        )
        self.car_gps_yes = self.car_gps_attribute_line.product_template_value_ids[0]
        self.car_gps_no = self.car_gps_attribute_line.product_template_value_ids[1]

        self.color_attribute = self.env["product.attribute"].create(
            {"name": "Color", "sequence": 1}
        )
        self.color_red = self.env["product.attribute.value"].create(
            {
                "name": "Red",
                "attribute_id": self.color_attribute.id,
                "sequence": 1,
            }
        )
        self.color_blue = self.env["product.attribute.value"].create(
            {
                "name": "Blue",
                "attribute_id": self.color_attribute.id,
                "sequence": 2,
            }
        )

        self.car_color_attribute_line = self.env[
            "product.template.attribute.line"
        ].create(
            {
                "product_tmpl_id": self.car.id,
                "attribute_id": self.color_attribute.id,
                "value_ids": [(6, 0, [self.color_red.id, self.color_blue.id])],
            }
        )
        self.car_color_red = self.car_color_attribute_line.product_template_value_ids[0]
        self.car_color_blue = self.car_color_attribute_line.product_template_value_ids[
            1
        ]

        uom_litre = self.env.ref("uom.product_uom_litre")
        self.paint = self.env["product.template"].create(
            {"name": "Paint", "uom_id": uom_litre.id}
        )
        self.paint_color_attribute_line = self.env[
            "product.template.attribute.line"
        ].create(
            {
                "product_tmpl_id": self.paint.id,
                "attribute_id": self.color_attribute.id,
                "value_ids": [(6, 0, [self.color_red.id, self.color_blue.id])],
            }
        )
        self.paint_color_red = (
            self.paint_color_attribute_line.product_template_value_ids[0]
        )
        self.paint_color_blue = (
            self.paint_color_attribute_line.product_template_value_ids[1]
        )

        self.paint.product_variant_ids.write({"standard_price": 20})

        self.dashboard = self.env["product.template"].create(
            {
                "name": "Dashboard",
                "standard_price": 1000,
            }
        )

        self.dashboard_gps_attribute_line = self.env[
            "product.template.attribute.line"
        ].create(
            {
                "product_tmpl_id": self.dashboard.id,
                "attribute_id": self.gps_attribute.id,
                "value_ids": [(6, 0, [self.gps_yes.id, self.gps_no.id])],
            }
        )
        self.dashboard_gps_yes = (
            self.dashboard_gps_attribute_line.product_template_value_ids[0]
        )
        self.dashboard_gps_no = (
            self.dashboard_gps_attribute_line.product_template_value_ids[1]
        )

        self.dashboard_color_attribute_line = self.env[
            "product.template.attribute.line"
        ].create(
            {
                "product_tmpl_id": self.dashboard.id,
                "attribute_id": self.color_attribute.id,
                "value_ids": [(6, 0, [self.color_red.id, self.color_blue.id])],
            }
        )
        self.dashboard_color_red = (
            self.dashboard_color_attribute_line.product_template_value_ids[0]
        )
        self.dashboard_color_blue = (
            self.dashboard_color_attribute_line.product_template_value_ids[1]
        )

        self.gps = self.env["product.product"].create(
            {
                "name": "GPS",
                "standard_price": 700,
            }
        )

        bom_form_car = Form(self.env["mrp.bom"])
        bom_form_car.product_tmpl_id = self.car
        bom_form_car.product_qty = 5
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(
                self.paint_color_red
            )
            line.product_uom_id = uom_litre
            line.product_qty = 50
            line.bom_product_template_attribute_value_ids.add(self.car_color_red)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(
                self.paint_color_blue
            )
            line.product_uom_id = uom_litre
            line.product_qty = 50
            line.bom_product_template_attribute_value_ids.add(self.car_color_blue)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(
                self.dashboard_gps_yes + self.dashboard_color_red
            )
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_yes)
            line.bom_product_template_attribute_value_ids.add(self.car_color_red)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(
                self.dashboard_gps_yes + self.dashboard_color_blue
            )
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_yes)
            line.bom_product_template_attribute_value_ids.add(self.car_color_blue)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(
                self.dashboard_gps_no + self.dashboard_color_red
            )
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_no)
            line.bom_product_template_attribute_value_ids.add(self.car_color_red)
        with bom_form_car.bom_line_ids.new() as line:
            line.product_id = self.dashboard._get_variant_for_combination(
                self.dashboard_gps_no + self.dashboard_color_blue
            )
            line.product_qty = 5
            line.bom_product_template_attribute_value_ids.add(self.car_gps_no)
            line.bom_product_template_attribute_value_ids.add(self.car_color_blue)
        bom_car = bom_form_car.save()

        bom_dashboard = Form(self.env["mrp.bom"])
        bom_dashboard.product_tmpl_id = self.dashboard
        bom_dashboard.product_qty = 2
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(
                self.paint_color_red
            )
            line.product_uom_id = uom_litre
            line.product_qty = 1
            line.bom_product_template_attribute_value_ids.add(self.dashboard_color_red)
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.paint._get_variant_for_combination(
                self.paint_color_blue
            )
            line.product_uom_id = uom_litre
            line.product_qty = 1
            line.bom_product_template_attribute_value_ids.add(self.dashboard_color_blue)
        with bom_dashboard.bom_line_ids.new() as line:
            line.product_id = self.gps
            line.product_qty = 2
            line.bom_product_template_attribute_value_ids.add(self.dashboard_gps_yes)
        bom_dashboard = bom_dashboard.save()

        blue_car_with_gps = self.car._get_variant_for_combination(
            self.car_color_blue + self.car_gps_yes
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_car.id, searchQty=1, searchVariant=blue_car_with_gps.id
        )
        self.assertEqual(len(report_values["lines"]["components"]), 2)

        blue_paint = self.paint._get_variant_for_combination(self.paint_color_blue)
        self.assertEqual(
            blue_paint.id, report_values["lines"]["components"][0]["product"].id
        )
        self.assertEqual(report_values["lines"]["components"][0]["quantity"], 10)
        blue_dashboard_gps = self.dashboard._get_variant_for_combination(
            self.dashboard_color_blue + self.dashboard_gps_yes
        )
        self.assertEqual(
            blue_dashboard_gps.id, report_values["lines"]["components"][1]["product"].id
        )
        self.assertEqual(report_values["lines"]["components"][1]["quantity"], 1)
        report_values_dashboad = report_values["lines"]["components"][1]

        self.assertEqual(len(report_values_dashboad["components"]), 2)
        self.assertEqual(
            blue_paint.id, report_values_dashboad["components"][0]["product"].id
        )
        self.assertEqual(
            self.gps.id, report_values_dashboad["components"][1]["product"].id
        )

        self.assertEqual(report_values_dashboad["components"][0]["bom_cost"], 10)
        self.assertEqual(report_values_dashboad["components"][1]["bom_cost"], 700)

        self.assertEqual(report_values["lines"]["components"][1]["bom_cost"], 710)
        self.assertEqual(report_values["lines"]["components"][0]["bom_cost"], 200)

        self.assertEqual(report_values["lines"]["bom_cost"], 910)

        red_car_without_gps = self.car._get_variant_for_combination(
            self.car_color_red + self.car_gps_no
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_car.id, searchQty=1, searchVariant=red_car_without_gps.id
        )
        self.assertEqual(report_values["lines"]["bom_cost"], 210)

    def test_22_bom_report_recursive_bom(self):
        uom_litre = self.env.ref("uom.product_uom_litre")

        finished = self.env["product.product"].create(
            {
                "name": "Finished",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )

        semi_finished = self.env["product.product"].create(
            {
                "name": "Semi-Finished",
                "is_storable": True,
                "uom_id": self.uom_kg.id,
            }
        )

        assembly = self.env["product.product"].create(
            {
                "name": "Assembly",
                "is_storable": True,
                "uom_id": self.uom_dozen.id,
            }
        )

        raw_material = self.env["product.product"].create(
            {
                "name": "Raw Material",
                "is_storable": True,
                "uom_id": uom_litre.id,
                "standard_price": 5,
            }
        )

        bom_finished = Form(self.env["mrp.bom"])
        bom_finished.product_tmpl_id = finished.product_tmpl_id
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = semi_finished
            line.product_uom_id = self.uom_kg
            line.product_qty = 5
        bom_finished = bom_finished.save()

        bom_semi_finished = Form(self.env["mrp.bom"])
        bom_semi_finished.product_tmpl_id = semi_finished.product_tmpl_id
        bom_semi_finished.product_qty = 11
        with bom_semi_finished.bom_line_ids.new() as line:
            line.product_id = assembly
            line.product_uom_id = self.uom_dozen
            line.product_qty = 2
        bom_semi_finished = bom_semi_finished.save()

        bom_assembly = Form(self.env["mrp.bom"])
        bom_assembly.product_tmpl_id = assembly.product_tmpl_id
        bom_assembly.product_qty = 5
        with bom_assembly.bom_line_ids.new() as line:
            line.product_id = raw_material
            line.product_uom_id = uom_litre
            line.product_qty = 4
        bom_assembly = bom_assembly.save()

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom_finished.id, searchQty=80
        )

        self.assertAlmostEqual(report_values["lines"]["bom_cost"], 2.92)

    def test_bom_report_capacity_with_quantity_of_0(self):
        target = self.env["product.product"].create(
            {
                "name": "Target",
                "is_storable": True,
            }
        )

        product_one = self.env["product.product"].create(
            {
                "name": "Component one",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product_one, self.stock_location, 3.0
        )

        product_two = self.env["product.product"].create(
            {
                "name": "Component two",
                "is_storable": True,
            }
        )
        self.env["stock.quant"]._update_available_quantity(
            product_two, self.stock_location, 4.0
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": target.product_tmpl_id.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": product_one.id,
                            "product_qty": 0,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": product_two.id,
                            "product_qty": 0.1,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom.id
        )

        self.assertEqual(report_values["lines"]["producible_qty"], 40)

    def test_bom_report_capacity_with_duplicate_components(self):
        self.env["stock.quant"]._update_available_quantity(
            self.product_2, self.stock_location, 2.0
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_3.product_tmpl_id.id,
                "product_qty": 1,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 2,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 2,
                        }
                    ),
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom.id
        )
        self.assertEqual(report_values["lines"]["producible_qty"], 0)

    def test_bom_report_same_component(self):
        final_product_tmpl = self.env["product.template"].create(
            {"name": "Final Product", "is_storable": True}
        )
        component_product = self.env["product.product"].create(
            {"name": "Compo 1", "is_storable": True}
        )

        self.env["stock.quant"]._update_available_quantity(
            component_product, self.stock_location, 3.0
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": final_product_tmpl.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": component_product.id,
                            "product_qty": 3,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": component_product.id,
                            "product_qty": 3,
                            "product_uom_id": self.uom_unit.id,
                        }
                    ),
                ],
            }
        )

        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=bom.id
        )
        line_values = report_values["lines"]["components"][0]
        self.assertEqual(
            line_values["availability_state"],
            "unavailable",
            "The merged components should be unavailable",
        )

    def test_report_data_bom_with_0_qty(self):
        self.bom_4.bom_line_ids = [
            Command.create(
                {
                    "product_id": self.bom_2.product_id.id,
                    "product_qty": 1.0,
                }
            )
        ]
        self.bom_4.bom_line_ids.product_qty = 0
        report_values = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom_id=self.bom_4.id, searchQty=1, searchVariant=False
        )

        self.assertEqual(
            sum(
                value["quantity"] for value in report_values["lines"]["components"][:2]
            ),
            0,
            "The quantity should be set to 0 for all components of the bom.",
        )

    def test_validate_no_bom_line_with_same_product(self):
        finished = self.env["product.product"].create(
            {
                "name": "Finished",
                "is_storable": True,
                "uom_id": self.uom_unit.id,
            }
        )
        bom_finished = Form(self.env["mrp.bom"])
        bom_finished.product_tmpl_id = finished.product_tmpl_id
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = finished
            line.product_uom_id = self.uom_unit
            line.product_qty = 5
        with self.assertRaises(exceptions.ValidationError):
            bom_finished = bom_finished.save()

    def test_validate_no_bom_line_with_same_product_variant(self):
        bom_finished = Form(self.env["mrp.bom"])
        bom_finished.product_tmpl_id = self.product_7_template
        bom_finished.product_id = self.product_7_3
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = self.product_7_3
            line.product_uom_id = self.uom_unit
            line.product_qty = 5
        with self.assertRaises(exceptions.ValidationError):
            bom_finished = bom_finished.save()

    def test_validate_bom_line_with_different_product_variant(self):
        bom_finished = Form(self.env["mrp.bom"])
        bom_finished.product_tmpl_id = self.product_7_template
        bom_finished.product_id = self.product_7_3
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = self.product_7_2
            line.product_uom_id = self.uom_unit
            line.product_qty = 5
        bom_finished = bom_finished.save()

    def test_validate_bom_line_with_variant_of_bom_product(self):
        bom_finished = Form(self.env["mrp.bom"])
        bom_finished.product_tmpl_id = self.product_6.product_tmpl_id
        bom_finished.product_qty = 100
        with bom_finished.bom_line_ids.new() as line:
            line.product_id = self.product_7_2
            line.product_uom_id = self.uom_unit
            line.product_qty = 5
        bom_finished = bom_finished.save()

    def test_replenishment(self):

        product_gram = self.env["product.product"].create(
            {
                "name": "Product sold in grams",
                "is_storable": True,
                "uom_id": self.uom_gm.id,
                "route_ids": [Command.link(self.route_manufacture.id)],
            }
        )
        self.env["mrp.bom"].create(
            {
                "product_id": product_gram.id,
                "product_tmpl_id": product_gram.product_tmpl_id.id,
                "product_uom_id": self.uom_kg.id,
                "product_qty": 2.0,
                "type": "normal",
            }
        )
        picking_form = Form(self.env["stock.picking"])
        picking_form.picking_type_id = self.picking_type_out
        with picking_form.move_ids.new() as move:
            move.product_id = product_gram
            move.product_uom_qty = 2300.0
        customer_picking = picking_form.save()
        customer_picking.action_confirm()

        self.env.flush_all()
        self.env["stock.warehouse.orderpoint"]._prepare_action_orderpoint_replenish()
        orderpoint = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "=", product_gram.id)]
        )
        orderpoint.replenishment_uom_id = self.uom_kg
        self.assertEqual(orderpoint.route_id.id, False)
        self.assertEqual(orderpoint.qty_to_order, 3000.0)

    def test_bom_generated_from_mo(self):
        common_vals = {"is_storable": True}
        finished_product = self.env["product.product"].create(
            dict(common_vals, name="Monster in Jar")
        )
        component_1 = self.env["product.product"].create(
            dict(common_vals, name="Monster")
        )
        component_2 = self.env["product.product"].create(dict(common_vals, name="Jar"))
        by_product = self.env["product.product"].create(
            dict(common_vals, name="Monster's Tears")
        )

        def create_mo(qty_to_produce=1):
            mo_form = Form(self.env["mrp.production"])
            mo_form.product_id = finished_product
            mo_form.product_qty = qty_to_produce
            for component in [component_1, component_2]:
                with mo_form.move_raw_ids.new() as raw_move:
                    raw_move.product_id = component
                    raw_move.product_uom_qty = qty_to_produce
            return mo_form.save()

        def generate_bom_from_mo(mo):
            action_generate_new_bom = mo.action_generate_bom()
            return Form(
                self.env["mrp.bom"].with_context(action_generate_new_bom["context"])
            ).save()

        mo_1 = create_mo()
        bom_from_mo_1 = generate_bom_from_mo(mo_1)
        self.assertEqual(
            mo_1.bom_id, bom_from_mo_1, "New BoM was assigned to the draft MO"
        )
        self.assertEqual(len(mo_1.move_raw_ids), 2)
        self.assertEqual(
            mo_1.move_raw_ids[0].bom_line_id, bom_from_mo_1.bom_line_ids[0]
        )
        self.assertEqual(
            mo_1.move_raw_ids[1].bom_line_id, bom_from_mo_1.bom_line_ids[1]
        )
        self.assertEqual(bom_from_mo_1.product_id, finished_product)
        self.assertRecordValues(
            bom_from_mo_1.bom_line_ids,
            [
                {"product_id": component_1.id, "product_qty": 1},
                {"product_id": component_2.id, "product_qty": 1},
            ],
        )
        bom_from_mo_1.active = False

        mo_2 = create_mo()
        mo_2.action_confirm()
        mo_2.button_mark_done()
        move_ids = mo_2.move_raw_ids.ids
        bom_from_mo_2 = generate_bom_from_mo(mo_2)
        bom_lines = bom_from_mo_2.bom_line_ids
        self.assertEqual(
            mo_2.bom_id, bom_from_mo_2, "New BoM should be assigned to the done MO"
        )
        self.assertRecordValues(
            mo_2.move_raw_ids,
            [
                {
                    "bom_line_id": False,
                    "id": move_ids[0],
                    "product_id": bom_lines[0].product_id.id,
                },
                {
                    "bom_line_id": False,
                    "id": move_ids[1],
                    "product_id": bom_lines[1].product_id.id,
                },
            ],
        )
        self.assertEqual(bom_from_mo_2.product_id, finished_product)
        self.assertRecordValues(
            bom_from_mo_2.bom_line_ids,
            [
                {"product_id": component_1.id, "product_qty": 1},
                {"product_id": component_2.id, "product_qty": 1},
            ],
        )
        bom_from_mo_2.active = False

        self.env.user.group_ids += self.env.ref("mrp.group_mrp_byproducts")
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_routings")
        mo_3 = create_mo(3)
        mo_3.action_confirm()
        mo_form = Form(mo_3)
        with mo_form.workorder_ids.new() as operation:
            operation.name = "Kiss the Monster on its Forehead 😘"
            operation.workcenter_id = self.workcenter_1
            operation.duration_expected = 60
        with mo_form.workorder_ids.new() as operation:
            operation.name = "Put the Monster in the Jar!"
            operation.workcenter_id = self.workcenter_2
            operation.duration_expected = 480
        with mo_form.move_byproduct_ids.new() as by_product_line:
            by_product_line.product_id = by_product
            by_product_line.quantity = 6
        mo_3 = mo_form.save()
        bom_from_mo_3 = generate_bom_from_mo(mo_3)
        self.assertEqual(
            mo_3.bom_id, bom_from_mo_3, "New BoM was assigned to the confirmed MO"
        )
        self.assertEqual(
            mo_3.move_raw_ids[0].bom_line_id, bom_from_mo_3.bom_line_ids[0]
        )
        self.assertEqual(
            mo_3.move_raw_ids[1].bom_line_id, bom_from_mo_3.bom_line_ids[1]
        )
        self.assertEqual(
            mo_3.workorder_ids[0].operation_id, bom_from_mo_3.operation_ids[0]
        )
        self.assertEqual(
            mo_3.workorder_ids[1].operation_id, bom_from_mo_3.operation_ids[1]
        )
        self.assertEqual(
            mo_3.move_byproduct_ids.byproduct_id, bom_from_mo_3.byproduct_ids
        )
        self.assertEqual(mo_3.bom_id, bom_from_mo_3)
        self.assertEqual(bom_from_mo_3.product_id, finished_product)
        self.assertEqual(bom_from_mo_3.product_qty, 3)
        self.assertRecordValues(
            bom_from_mo_3.bom_line_ids,
            [
                {"product_id": component_1.id, "product_qty": 3},
                {"product_id": component_2.id, "product_qty": 3},
            ],
        )
        self.assertRecordValues(
            bom_from_mo_3.operation_ids,
            [
                {
                    "name": "Kiss the Monster on its Forehead 😘",
                    "workcenter_id": self.workcenter_1.id,
                    "time_cycle": 20,
                },
                {
                    "name": "Put the Monster in the Jar!",
                    "workcenter_id": self.workcenter_2.id,
                    "time_cycle": 160,
                },
            ],
        )
        self.assertEqual(bom_from_mo_3.byproduct_ids.product_id, by_product)
        self.assertEqual(bom_from_mo_3.byproduct_ids.product_qty, 6)

    def test_bom_generated_from_mo_with_different_uom(self):
        self.env.user.group_ids += self.env.ref("uom.group_uom")
        common_vals = {"is_storable": True}
        finished_product = self.env["product.product"].create(
            dict(common_vals, name="CO² Molecule")
        )
        component_1 = self.env["product.product"].create(
            dict(common_vals, name="Carbon Molecule")
        )
        component_2 = self.env["product.product"].create(
            dict(common_vals, name="Oxygen Molecule")
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = finished_product
        mo_form.product_qty = 1
        mo_form.product_uom_id = self.uom_dozen
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_1
            raw_move.product_uom_qty = 12
            raw_move.product_uom_id = self.uom_unit
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_2
            raw_move.product_uom_qty = 2
            raw_move.product_uom_id = self.uom_dozen
        mo = mo_form.save()
        mo.action_confirm()
        action_generate_new_bom = mo.action_generate_bom()
        bom_form = Form(
            self.env["mrp.bom"].with_context(action_generate_new_bom["context"])
        )
        bom_from_mo = bom_form.save()
        self.assertEqual(bom_from_mo.product_uom_id, self.uom_dozen)
        self.assertEqual(bom_from_mo.product_qty, 1)
        self.assertRecordValues(
            bom_from_mo.bom_line_ids,
            [
                {
                    "product_id": component_1.id,
                    "product_qty": 12,
                    "product_uom_id": self.uom_unit.id,
                },
                {
                    "product_id": component_2.id,
                    "product_qty": 2,
                    "product_uom_id": self.uom_dozen.id,
                },
            ],
        )

    def test_bom_generated_from_mo_with_byproducts(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_byproducts")
        common_vals = {"is_storable": True}
        finished_product = self.env["product.product"].create(
            dict(common_vals, name="Banana Bread")
        )
        component_1 = self.env["product.product"].create(
            dict(common_vals, name="Banana")
        )
        component_2 = self.env["product.product"].create(
            dict(common_vals, name="Sugar, Spice and Everything Nice")
        )
        by_product = self.env["product.product"].create(
            dict(common_vals, name="Banana Peels")
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = finished_product
        mo_form.product_qty = 1
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_1
            raw_move.product_uom_qty = 1
        with mo_form.move_raw_ids.new() as raw_move:
            raw_move.product_id = component_2
            raw_move.product_uom_qty = 1
        with mo_form.move_byproduct_ids.new() as by_product_move:
            by_product_move.product_id = by_product
            by_product_move.product_uom_qty = 1
            by_product_move.cost_share = 50
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.move_byproduct_ids.cost_share, 50)
        action_generate_new_bom = mo.action_generate_bom()
        bom_form = Form(
            self.env["mrp.bom"].with_context(action_generate_new_bom["context"])
        )
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_qty = 3
        with bom_form.byproduct_ids.edit(0) as bom_by_product:
            bom_by_product.product_qty = 3
            bom_by_product.cost_share = 10
        bom_from_mo = bom_form.save()
        self.assertEqual(mo.bom_id, bom_from_mo)
        self.assertEqual(mo.move_raw_ids[0].product_uom_qty, 3)
        self.assertEqual(mo.move_raw_ids[1].product_uom_qty, 1)
        self.assertEqual(mo.move_byproduct_ids.cost_share, 10)
        self.assertEqual(mo.move_byproduct_ids.product_uom_qty, 3)

    def test_bom_kit_with_sub_kit(self):
        p1, p2, p3, p4, p5, p6 = self.make_prods(6)
        prod1, prod2 = self.make_prods(2)
        self.make_bom(p1, p2, p3)
        self.make_bom(p2, p3, p4)
        bom = self.make_bom(p5, p6)
        bom.bom_line_ids[0].product_qty = 0.1
        bom = self.make_bom(prod1, prod2)
        bom.product_qty = 100

        self.env["stock.quant"]._update_available_quantity(p3, self.stock_location, 10)
        self.env["stock.quant"]._update_available_quantity(p4, self.stock_location, 10)
        self.env["stock.quant"]._update_available_quantity(p6, self.stock_location, 5.5)
        self.env["stock.quant"]._update_available_quantity(
            p6, self.stock_location, -4.8
        )
        self.env["stock.quant"]._update_available_quantity(
            prod2, self.stock_location, 5.57
        )
        self.env["stock.quant"]._update_available_quantity(
            prod2, self.stock_location, -5
        )

        self.assertEqual(p1.qty_available, 5.0)
        self.assertEqual(p2.qty_available, 10.0)
        self.assertEqual(p3.qty_available, 10.0)
        self.assertEqual(p5.qty_available, 7.0)
        self.assertEqual(prod1.qty_available, 57.0)

    def test_bom_updates_mo(self):
        self.env.user.group_ids += self.env.ref("mrp.group_mrp_byproducts")
        common_vals = {"is_storable": True}
        finished_product = self.env["product.product"].create(
            dict(common_vals, name="Monster in Jar")
        )
        component_1 = self.env["product.product"].create(
            dict(common_vals, name="Monster")
        )
        component_2 = self.env["product.product"].create(dict(common_vals, name="Jar"))
        component_3 = self.env["product.product"].create(
            dict(common_vals, name="Bottle")
        )
        by_product = self.env["product.product"].create(
            dict(common_vals, name="Monster's Tears")
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": p.id, "product_qty": 1})
                    for p in [component_1, component_2, component_3]
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Operation to delete",
                            "workcenter_id": self.workcenter_1.id,
                        }
                    )
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_form.product_qty = 10
        mo_1 = mo_form.save()
        self.assertEqual(mo_1.move_raw_ids[0].product_uom_qty, 10)
        self.assertEqual(mo_1.is_outdated_bom, False)
        mo_form = Form(mo_1)
        with mo_form.move_raw_ids.edit(0) as raw_move:
            raw_move.product_uom_qty = 123
        mo_1 = mo_form.save()
        initial_move_raws = mo_1.move_raw_ids
        inital_workorder_ids = mo_1.workorder_ids
        self.assertEqual(mo_1.move_raw_ids[0].product_uom_qty, 123)
        self.assertEqual(
            mo_1.is_outdated_bom,
            False,
            "Making a modification in the MO shouldn't mark the BoM as updated",
        )

        bom.byproduct_ids = [
            Command.create({"product_id": by_product.id, "product_qty": 2})
        ]
        bom_byproduct = bom.byproduct_ids
        bom.operation_ids = [
            Command.clear(),
            Command.create(
                {
                    "name": "Gently insert the Monster in the Jar",
                    "workcenter_id": self.workcenter_1.id,
                }
            ),
        ]
        operation = bom.operation_ids

        self.assertEqual(
            mo_1.is_outdated_bom,
            True,
            "By-Product and Operation were added to the BoM, it should be marked as updated",
        )
        bom.bom_line_ids = bom.bom_line_ids[:-1]
        mo_1.action_update_bom()
        self.assertEqual(mo_1.product_qty, 10, "MO's quantity should be kept")
        self.assertEqual(
            mo_1.is_outdated_bom,
            False,
            "After 'Update BoM' action, MO's BoM should no longer be marked as updated",
        )
        self.assertEqual(mo_1.workorder_ids.operation_id.id, operation.id)
        self.assertEqual(mo_1.move_byproduct_ids.byproduct_id.id, bom_byproduct.id)
        self.assertTrue(initial_move_raws - mo_1.move_raw_ids)
        self.assertFalse((initial_move_raws - mo_1.move_raw_ids).exists())
        self.assertTrue(inital_workorder_ids - mo_1.workorder_ids)
        self.assertFalse((inital_workorder_ids - mo_1.workorder_ids).exists())

        mo_1.action_confirm()
        self.assertEqual(
            mo_1.is_outdated_bom,
            False,
            "After 'Update BoM' action, MO's BoM should no longer be marked as updated",
        )
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_qty += 1
        bom = bom_form.save()
        self.assertEqual(
            mo_1.is_outdated_bom,
            True,
            "BoM line's quantity was update, the BoM should be marked as updated",
        )
        mo_1.action_update_bom()
        self.assertEqual(
            mo_1.is_outdated_bom,
            False,
            "After 'Update BoM' action, MO's BoM should no longer be marked as updated",
        )
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {
                    "bom_line_id": bom.bom_line_ids[0].id,
                    "product_uom_qty": bom.bom_line_ids[0].product_qty * 10,
                },
                {
                    "bom_line_id": bom.bom_line_ids[1].id,
                    "product_uom_qty": bom.bom_line_ids[1].product_qty * 10,
                },
            ],
        )
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.product_id = component_3
        bom = bom_form.save()
        self.assertEqual(
            mo_1.is_outdated_bom,
            True,
            "A component was changed, BoM should be marked as updated",
        )
        mo_1.action_update_bom()
        self.assertEqual(
            mo_1.is_outdated_bom,
            False,
            "There should be no difference between the MO and BoM",
        )
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {"bom_line_id": bom.bom_line_ids[0].id, "product_id": component_1.id},
                {"bom_line_id": bom.bom_line_ids[1].id, "product_id": component_3.id},
            ],
        )

        bom_form = Form(bom)
        bom_form.bom_line_ids.remove(1)
        bom = bom_form.save()
        self.assertEqual(
            mo_1.is_outdated_bom,
            True,
            "A component was changed, BoM should be marked as updated",
        )
        mo_1.action_update_bom()
        self.assertEqual(
            mo_1.is_outdated_bom,
            False,
            "There should be no difference between the MO and BoM",
        )
        self.assertEqual(len(mo_1.move_raw_ids), 1)

        with bom_form.byproduct_ids.edit(0) as byproduct_line:
            byproduct_line.product_qty += 1
        bom = bom_form.save()
        self.assertEqual(
            mo_1.is_outdated_bom,
            True,
            "BoM byproduct's quantity was update, BoM should be marked as updated",
        )
        mo_1.action_update_bom()
        self.assertEqual(
            mo_1.is_outdated_bom,
            False,
            "There should be no difference between the MO and BoM",
        )
        self.assertEqual(
            mo_1.move_byproduct_ids.product_uom_qty, bom.byproduct_ids.product_qty * 10
        )

        bom.product_qty *= 3
        bom.bom_line_ids[0].product_qty *= 3
        bom.byproduct_ids.product_qty *= 3
        self.assertEqual(
            mo_1.is_outdated_bom,
            True,
            "Even if the BoM's changes don't imply actual changes for the MO, it should be marked as updated.",
        )

    def test_bom_updates_mo_with_different_uom(self):
        self.env.user.group_ids += self.env.ref("uom.group_uom")
        common_vals = {"is_storable": True}
        finished_product = self.env["product.product"].create(
            dict(common_vals, name="Monster in Jar")
        )
        component_1 = self.env["product.product"].create(
            dict(common_vals, name="Monster")
        )
        component_2 = self.env["product.product"].create(dict(common_vals, name="Jar"))
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_qty": 2.0,
                "bom_line_ids": [
                    Command.create({"product_id": p.id, "product_qty": 1})
                    for p in [component_1, component_2]
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_form.product_qty = 4
        mo_form.product_uom_id = self.uom_dozen
        mo_1 = mo_form.save()
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {
                    "product_id": component_1.id,
                    "product_uom_qty": 24,
                    "product_uom_id": self.uom_unit.id,
                },
                {
                    "product_id": component_2.id,
                    "product_uom_qty": 24,
                    "product_uom_id": self.uom_unit.id,
                },
            ],
        )

        bom.product_qty = 1
        self.assertEqual(
            mo_1.is_outdated_bom, True, "BoM changed, it should be marked as updated."
        )
        mo_1.action_update_bom()
        self.assertRecordValues(
            mo_1, [{"product_qty": 4, "product_uom_id": self.uom_dozen.id}]
        )
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {
                    "product_id": component_1.id,
                    "product_uom_qty": 48,
                    "product_uom_id": self.uom_unit.id,
                },
                {
                    "product_id": component_2.id,
                    "product_uom_qty": 48,
                    "product_uom_id": self.uom_unit.id,
                },
            ],
        )

        mo_1.product_qty = 1
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {
                    "product_id": component_1.id,
                    "product_uom_qty": 12,
                    "product_uom_id": self.uom_unit.id,
                },
                {
                    "product_id": component_2.id,
                    "product_uom_qty": 12,
                    "product_uom_id": self.uom_unit.id,
                },
            ],
        )
        mo_1.action_confirm()
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_qty = 2
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)

        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False)
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {
                    "product_id": component_1.id,
                    "product_uom_qty": 24,
                    "product_uom_id": self.uom_unit.id,
                },
                {
                    "product_id": component_2.id,
                    "product_uom_qty": 12,
                    "product_uom_id": self.uom_unit.id,
                },
            ],
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_form.product_uom_id = self.uom_dozen
        with mo_form.move_raw_ids.edit(0) as move_raw:
            move_raw.product_uom_qty = 2
            move_raw.product_uom_id = self.uom_dozen
        with mo_form.move_raw_ids.edit(1) as move_raw:
            move_raw.product_uom_qty = 1
            move_raw.product_uom_id = self.uom_dozen
        mo_2 = mo_form.save()
        self.assertEqual(mo_2.state, "draft")
        mo_2.action_confirm()
        self.assertEqual(mo_2.state, "confirmed")
        self.assertRecordValues(
            mo_2.move_raw_ids,
            [
                {
                    "product_id": component_1.id,
                    "product_uom_qty": 2,
                    "product_uom_id": self.uom_dozen.id,
                },
                {
                    "product_id": component_2.id,
                    "product_uom_qty": 1,
                    "product_uom_id": self.uom_dozen.id,
                },
            ],
        )
        mo_form = Form(mo_2)
        with mo_form.move_raw_ids.edit(0) as move_raw:
            move_raw.quantity = 5
        with mo_form.move_raw_ids.edit(1) as move_raw:
            move_raw.quantity = 5
        mo_2 = mo_form.save()

        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.product_qty = 2
        bom = bom_form.save()
        self.assertEqual(mo_2.is_outdated_bom, False)

    def test_bom_updates_mo_after_updating_operations(self):
        common_vals = {"is_storable": True}
        finished_product = self.env["product.product"].create(
            dict(common_vals, name="Monster in Jar")
        )
        component_1 = self.env["product.product"].create(
            dict(common_vals, name="Monster")
        )
        component_2 = self.env["product.product"].create(dict(common_vals, name="Jar"))
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished_product.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": p.id, "product_qty": 1})
                    for p in [component_1, component_2]
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "OP1",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 10,
                            "sequence": 1,
                        }
                    ),
                    Command.create(
                        {
                            "name": "OP2",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 15,
                            "sequence": 2,
                        }
                    ),
                ],
            }
        )
        bom.bom_line_ids[0].operation_id = bom.operation_ids[0].id
        bom.bom_line_ids[1].operation_id = bom.operation_ids[1].id
        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = bom
        mo_1 = mo_form.save()
        mo_1.action_confirm()
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {
                    "operation_id": bom.operation_ids[0].id,
                    "workorder_id": mo_1.workorder_ids[0].id,
                },
                {
                    "operation_id": bom.operation_ids[1].id,
                    "workorder_id": mo_1.workorder_ids[1].id,
                },
            ],
        )

        self.env["mrp.routing.workcenter"].create(
            {"name": "OP3", "bom_id": bom.id, "workcenter_id": self.workcenter_1.id}
        )
        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.operation_id = bom.operation_ids[2]
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.operation_id = bom.operation_ids[0]
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False)
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {
                    "operation_id": bom.operation_ids[2].id,
                    "workorder_id": mo_1.workorder_ids[2].id,
                },
                {
                    "operation_id": bom.operation_ids[0].id,
                    "workorder_id": mo_1.workorder_ids[0].id,
                },
            ],
        )

        bom_form = Form(bom)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.operation_id = self.env["mrp.routing.workcenter"]
        with bom_form.bom_line_ids.edit(1) as bom_line:
            bom_line.operation_id = self.env["mrp.routing.workcenter"]
        bom = bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)
        mo_1.action_update_bom()
        self.assertEqual(mo_1.is_outdated_bom, False)
        self.assertRecordValues(
            mo_1.move_raw_ids,
            [
                {"operation_id": False, "workorder_id": False},
                {"operation_id": False, "workorder_id": False},
            ],
        )

    def test_bom_updates_mo_with_pre_prod_picking(self):
        self.env.user.group_ids += self.env.ref("stock.group_adv_location")
        self.warehouse_1.manufacture_steps = "pbm"

        mo_form = Form(self.env["mrp.production"])
        mo_form.bom_id = self.bom_1
        mo_form.picking_type_id = self.picking_type_manu
        mo_1 = mo_form.save()
        mo_1.action_confirm()
        picking = mo_1.picking_ids
        self.assertRecordValues(
            picking.move_ids,
            [
                {"product_id": self.product_2.id, "product_uom_qty": 2},
                {"product_id": self.product_1.id, "product_uom_qty": 4},
            ],
        )

        bom_form = Form(self.bom_1)
        with bom_form.bom_line_ids.edit(0) as bom_line:
            bom_line.product_id = self.product_3
        bom_form.save()
        self.assertEqual(mo_1.is_outdated_bom, True)
        mo_1.action_update_bom()
        self.assertRecordValues(
            picking.move_ids,
            [
                {
                    "product_id": self.product_2.id,
                    "product_uom_qty": 0,
                },
                {"product_id": self.product_1.id, "product_uom_qty": 4},
                {"product_id": self.product_3.id, "product_uom_qty": 2},
            ],
        )

    def test_operation_blocked_by_another_operation(self):
        ProductAttribute = self.env["product.attribute"]
        ProductAttributeValue = self.env["product.attribute.value"]

        att_color = ProductAttribute.create({"name": "Color", "sequence": 1})
        att_size = ProductAttribute.create({"name": "size", "sequence": 2})

        att_color_red = ProductAttributeValue.create(
            {"name": "red", "attribute_id": att_color.id, "sequence": 1}
        )
        att_color_blue = ProductAttributeValue.create(
            {"name": "blue", "attribute_id": att_color.id, "sequence": 2}
        )
        att_size_big = ProductAttributeValue.create(
            {"name": "big", "attribute_id": att_size.id, "sequence": 1}
        )
        att_size_medium = ProductAttributeValue.create(
            {"name": "medium", "attribute_id": att_size.id, "sequence": 2}
        )

        product_template = self.env["product.template"].create(
            {
                "name": "Sofa",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": att_color.id,
                            "value_ids": [
                                (6, 0, [att_color_red.id, att_color_blue.id])
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "attribute_id": att_size.id,
                            "value_ids": [
                                (6, 0, [att_size_big.id, att_size_medium.id])
                            ],
                        }
                    ),
                ],
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": self.uom_unit.id,
                "product_qty": 1.0,
                "allow_operation_dependencies": True,
                "operation_ids": [
                    Command.create(
                        {
                            "name": "op1",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 1.0,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    att_color_blue.pav_attribute_line_ids.product_template_value_ids[
                                        0
                                    ].id
                                ),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "op2",
                            "workcenter_id": self.workcenter_1.id,
                            "time_cycle": 1.0,
                        }
                    ),
                ],
            }
        )
        bom.operation_ids[1].blocked_by_operation_ids = [
            Command.link(bom.operation_ids[0].id)
        ]

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product_template.product_variant_ids[0]
        mo_form.bom_id = bom
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product_template.product_variant_ids[2]
        mo_form.bom_id = bom
        mo_form.product_qty = 1.0
        mo = mo_form.save()
        mo.action_confirm()
        self.assertEqual(mo.state, "confirmed")
        mo.qty_producing = 1.0
        mo.action_assign()
        mo.button_plan()
        mo.button_mark_done()
        self.assertEqual(mo.state, "done")

    def test_cycle_on_line_creation(self):
        bom_1_finished_product = self.bom_1.product_id
        bom_2_finished_product = self.bom_2.product_id
        with self.assertRaises(exceptions.ValidationError):
            self.bom_1.bom_line_ids = [
                Command.create(
                    {"product_id": bom_1_finished_product.id, "product_qty": 1.0}
                )
            ]
        with self.assertRaises(exceptions.ValidationError):
            self.bom_1.bom_line_ids = [
                Command.create(
                    {"product_id": bom_2_finished_product.id, "product_qty": 1.0}
                )
            ]

    def test_cycle_on_line_update(self):
        lines = self.bom_1.bom_line_ids
        bom_2_finished_product = self.bom_2.product_id
        with self.assertRaises(exceptions.ValidationError):
            self.bom_1.bom_line_ids = [
                (1, lines[0].id, {"product_id": bom_2_finished_product.id})
            ]

    def test_cycle_on_bom_unarchive(self):
        finished_product = self.bom_1.product_id
        component = self.bom_1.bom_line_ids.product_id[0]
        self.bom_1.active = False
        self.env["mrp.bom"].create(
            {
                "product_id": component.id,
                "product_tmpl_id": component.product_tmpl_id.id,
                "product_uom_id": component.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": finished_product.id, "product_qty": 1.0}
                    ),
                ],
            }
        )
        with self.assertRaises(exceptions.ValidationError):
            self.bom_1.active = True

    def test_cycle_on_bom_creation(self):
        finished_product = self.bom_4.product_id
        component = self.bom_4.bom_line_ids.product_id
        with self.assertRaises(exceptions.ValidationError):
            self.env["mrp.bom"].create(
                {
                    "product_id": component.id,
                    "product_tmpl_id": component.product_tmpl_id.id,
                    "product_uom_id": component.uom_id.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create(
                            {"product_id": finished_product.id, "product_qty": 1.0}
                        ),
                    ],
                }
            )

    def test_indirect_cycle_on_bom_creation(self):
        product_A, product_B, product_C, product_D = self.env["product.product"].create(
            [{"name": "%s" % i} for i in range(4)]
        )
        self.env["mrp.bom"].create(
            [
                {
                    "product_id": finished.id,
                    "product_tmpl_id": finished.product_tmpl_id.id,
                    "product_uom_id": finished.uom_id.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": compo.id, "product_qty": 1.0}),
                    ],
                }
                for finished, compo in [
                    (product_A, product_D),
                    (product_A, product_B),
                    (product_B, product_C),
                ]
            ]
        )
        with self.assertRaises(exceptions.ValidationError):
            self.env["mrp.bom"].create(
                {
                    "product_id": product_C.id,
                    "product_tmpl_id": product_C.product_tmpl_id.id,
                    "product_uom_id": product_C.uom_id.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create(
                            {"product_id": product_A.id, "product_qty": 1.0}
                        ),
                    ],
                }
            )

    def test_cycle_on_bom_sequencing(self):
        product_A, product_B, product_C, product_D, product_E = self.env[
            "product.product"
        ].create([{"name": "%s" % i} for i in range(5)])
        boms = self.env["mrp.bom"].create(
            [
                {
                    "product_id": finished.id,
                    "product_tmpl_id": finished.product_tmpl_id.id,
                    "product_uom_id": finished.uom_id.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create({"product_id": compo.id, "product_qty": 1.0}),
                    ],
                }
                for finished, compo in [
                    (product_A, product_D),
                    (product_A, product_B),
                    (product_C, product_D),
                    (product_C, product_E),
                    (product_B, product_C),
                    (product_C, product_A),
                ]
            ]
        )

        boms.invalidate_recordset()
        for i, record in enumerate(
            boms[0] | boms[1] | boms[3] | boms[2] | boms[4] | boms[5]
        ):
            record.write({"sequence": i})

        with self.assertRaises(exceptions.ValidationError):
            for i, record in enumerate(
                boms[0] | boms[1] | boms[5] | boms[3] | boms[2] | boms[4]
            ):
                record.write({"sequence": i})

    def test_cycle_on_legit_apply_variants(self):
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.product_7_template.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "product_qty": 1.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 1.0,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(self.product_7_attr1_v2.id)
                            ],
                        }
                    ),
                ],
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_2.product_tmpl_id.id,
                "product_uom_id": self.product_2.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {"product_id": self.product_7_1.id, "product_qty": 1.0}
                    ),
                ],
            }
        )

    def test_component_when_bom_change(self):
        bom_1 = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.product_7_template.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )
        bom_2 = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_7_template.id,
                "product_uom_id": self.product_7_template.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )
        mo = self.env["mrp.production"].create(
            {
                "product_qty": 1.0,
                "bom_id": bom_1.id,
            }
        )
        self.assertEqual(mo.move_raw_ids.product_id, self.product_1)
        mo_form = Form(mo)
        mo_form.bom_id = bom_2
        self.assertEqual(
            mo_form.move_raw_ids._records[0]["product_id"], self.product_2.id
        )
        self.assertEqual(len(mo_form.move_raw_ids._records), 1)
        mo_form.bom_id = bom_1
        self.assertEqual(
            mo_form.move_raw_ids._records[0]["product_id"], self.product_1.id
        )
        self.assertEqual(len(mo_form.move_raw_ids._records), 1)

    def test_update_operations(self):

        mo_form = Form(self.env["mrp.production"].with_user(self.user_mrp_user))
        mo_form.product_id = self.product_7_1
        mo_form.product_qty = 1.0
        mo_form.bom_id = self.bom_2
        mo = mo_form.save()
        mo.action_confirm()

        self.bom_2.operation_ids.write(
            {"name": "Painting", "workcenter_id": self.workcenter_2.id}
        )
        self.assertTrue(mo.is_outdated_bom)

        mo.action_update_bom()
        self.assertEqual(self.bom_2.operation_ids.name, mo.workorder_ids.name)
        self.assertEqual(
            self.bom_2.operation_ids.workcenter_id, mo.workorder_ids.workcenter_id
        )

    def test_archive_operations(self):

        mo_form = Form(self.env["mrp.production"].with_user(self.user_mrp_user))

        mo_form.product_id = self.product_7_1
        mo_form.product_qty = 1.0
        mo_form.bom_id = self.bom_2
        mo_order = mo_form.save()
        mo_order.action_confirm()

        operation_ids = self.bom_2.operation_ids.ids
        self.bom_2.operation_ids.action_archive()
        self.assertTrue(mo_order.is_outdated_bom)

        mo_order.action_update_bom()
        self.assertEqual(len(mo_order.workorder_ids), 0)

        self.env["mrp.routing.workcenter"].browse(operation_ids).action_unarchive()
        self.assertTrue(mo_order.is_outdated_bom)
        mo_order.action_update_bom()
        self.assertEqual(len(mo_order.workorder_ids), 1)

    def test_update_bom_in_routing_workcenter(self):
        resource_calendar_std_id = self.env.ref("resource.resource_calendar_std").id
        mrp_workcenter_1 = self.env["mrp.workcenter"].create(
            {
                "name": "Drill Station 1",
                "resource_calendar_id": resource_calendar_std_id,
            }
        )
        p1, c1, c2, byproduct = self.make_prods(4)
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": p1.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": c1.id, "product_qty": 1.0}),
                    Command.create({"product_id": c2.id, "product_qty": 1.0}),
                ],
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": byproduct.id,
                            "product_uom_id": byproduct.uom_id.id,
                            "product_qty": 1.0,
                        }
                    )
                ],
            }
        )
        operation_1, operation_2 = self.env["mrp.routing.workcenter"].create(
            [
                {
                    "name": "Operation 1",
                    "workcenter_id": mrp_workcenter_1.id,
                    "bom_id": bom.id,
                },
                {
                    "name": "Operation 2",
                    "workcenter_id": mrp_workcenter_1.id,
                    "bom_id": bom.id,
                },
            ]
        )
        bom.bom_line_ids.operation_id = operation_1
        bom.byproduct_ids.operation_id = operation_1
        operation_2.blocked_by_operation_ids = operation_1
        self.assertEqual(operation_1.bom_id, bom)
        operation_1.bom_id = self.bom_1
        self.assertEqual(operation_1.bom_id, self.bom_1)
        self.assertFalse(bom.bom_line_ids.operation_id)
        self.assertFalse(bom.byproduct_ids.operation_id)
        self.assertFalse(operation_2.blocked_by_operation_ids)

    def test_bom_document(self):
        doc_product_bom = self.env["document.document"].create(
            {
                "name": "doc_product_bom",
                "attached_on_mrp": "bom",
                "res_id": self.product_4.id,
                "res_model": "product.product",
            }
        )

        self.env["document.document"].create(
            {
                "name": "doc_product_bom_archived",
                "active": False,
                "attached_on_mrp": "bom",
                "res_id": self.product_4.id,
                "res_model": "product.product",
            }
        )

        doc_template_bom = self.env["document.document"].create(
            {
                "name": "doc_template_bom",
                "attached_on_mrp": "bom",
                "res_id": self.product_4.product_tmpl_id.id,
                "res_model": "product.template",
            }
        )

        attachments = doc_template_bom.attachment_id + doc_product_bom.attachment_id

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_4.product_tmpl_id.id,
                "product_uom_id": self.product_4.product_tmpl_id.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
            }
        )

        self.assertEqual(bom._get_extra_attachments(), doc_template_bom.attachment_id)

        bom.product_id = self.product_4
        self.assertEqual(bom._get_extra_attachments(), attachments)

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_5.product_tmpl_id.id,
                "product_uom_id": self.product_5.product_tmpl_id.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_4.id,
                            "product_qty": 1,
                        }
                    ),
                ],
            }
        )

        self.assertEqual(bom.bom_line_ids.attachments_count, 2)
        action = bom.bom_line_ids.action_see_attachments()
        self.assertTrue(action["context"]["search_default_context_variant"])

        doc_product_bom.attached_on_mrp = "hidden"
        action = bom.bom_line_ids.action_see_attachments()
        self.assertFalse(action["context"]["search_default_context_variant"])

        doc_template_bom.attached_on_mrp = "hidden"
        action = bom.bom_line_ids.action_see_attachments()
        self.assertTrue(action["context"]["search_default_context_variant"])

    def test_compute_days_to_prepare_from_mo_if_unavailable(self):
        bom = self.bom_1
        product = bom.product_id
        product.route_ids = [Command.set([self.route_manufacture.id])]
        notification = bom.action_compute_bom_days()
        self.assertEqual(bom.days_to_prepare_mo, 0.0)
        self.assertEqual(
            (notification["type"], notification["tag"]),
            ("ir.actions.client", "display_notification"),
        )

    def test_bom_never_attribute(self):

        product_attribute_radio = self.env["product.attribute"].create(
            {
                "name": "PA",
                "display_type": "radio",
                "create_variant": "no_variant",
            }
        )
        product, bp1, bp2, bp3, bp4 = self.env["product.product"].create(
            [
                {
                    "name": name,
                }
                for name in ["test1", "bp1", "bp2", "bp3", "bp4"]
            ]
        )
        self.env["product.attribute.value"].create(
            [
                {
                    "name": "radio_PAV" + str(i),
                    "attribute_id": product_attribute_radio.id,
                }
                for i in range(3)
            ]
        )

        tmpl_attr_line_radio = self.env["product.template.attribute.line"].create(
            {
                "attribute_id": product_attribute_radio.id,
                "product_tmpl_id": self.product_1.product_tmpl_id.id,
                "value_ids": [(6, 0, product_attribute_radio.value_ids.ids)],
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_1.product_tmpl_id.id,
                "product_uom_id": self.product_1.product_tmpl_id.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 1,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_3.id,
                            "product_qty": 2,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        0
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": product.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        1
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product_8.id,
                            "product_qty": 10,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        1
                                    ].id
                                ),
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        2
                                    ].id
                                ),
                            ],
                        }
                    ),
                ],
                "operation_ids": [
                    Command.create(
                        {
                            "name": "OPE_ALL",
                            "workcenter_id": self.workcenter_1.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "OPE_VAR_1",
                            "workcenter_id": self.workcenter_1.id,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        0
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "OPE_VAR_2",
                            "workcenter_id": self.workcenter_1.id,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        1
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "name": "OPE_VAR_2_3",
                            "workcenter_id": self.workcenter_1.id,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        1
                                    ].id
                                ),
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        2
                                    ].id
                                ),
                            ],
                        }
                    ),
                ],
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": bp1.id,
                            "product_qty": 1.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": bp2.id,
                            "product_qty": 1.0,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        0
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": bp3.id,
                            "product_qty": 1.0,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        1
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": bp4.id,
                            "product_qty": 1.0,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        1
                                    ].id
                                ),
                                Command.link(
                                    tmpl_attr_line_radio.product_template_value_ids[
                                        2
                                    ].id
                                ),
                            ],
                        }
                    ),
                ],
            }
        )

        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product_1
        mo_order = mo_form.save()

        self.assertEqual(
            len(mo_order.move_raw_ids),
            1,
            "Only one move with no never_product_template_attribute_value_ids should be created",
        )
        self.assertEqual(mo_order.move_raw_ids.product_id, self.product_2)
        self.assertEqual(len(mo_order.workorder_ids), 1)
        self.assertEqual(mo_order.workorder_ids.name, "OPE_ALL")
        self.assertEqual(len(mo_order.move_byproduct_ids), 1)
        self.assertEqual(mo_order.move_byproduct_ids.product_id, bp1)

        mo_order.never_product_template_attribute_value_ids = (
            tmpl_attr_line_radio.product_template_value_ids[0]
        )
        self.assertEqual(len(mo_order.move_raw_ids), 2)
        self.assertEqual(
            mo_order.move_raw_ids.product_id, self.product_2 + self.product_3
        )
        self.assertEqual(len(mo_order.workorder_ids), 2)
        self.assertListEqual(
            mo_order.workorder_ids.mapped("name"), ["OPE_ALL", "OPE_VAR_1"]
        )
        self.assertEqual(len(mo_order.move_byproduct_ids), 2)
        self.assertEqual(mo_order.move_byproduct_ids.product_id, bp1 + bp2)

        mo_order.never_product_template_attribute_value_ids = (
            tmpl_attr_line_radio.product_template_value_ids[1]
            + tmpl_attr_line_radio.product_template_value_ids[2]
        )
        self.assertEqual(len(mo_order.move_raw_ids), 3)
        self.assertEqual(
            mo_order.move_raw_ids.product_id, self.product_2 + product + self.product_8
        )
        self.assertEqual(len(mo_order.workorder_ids), 3)
        self.assertListEqual(
            mo_order.workorder_ids.mapped("name"),
            ["OPE_ALL", "OPE_VAR_2", "OPE_VAR_2_3"],
        )
        self.assertEqual(len(mo_order.move_byproduct_ids), 3)
        self.assertEqual(mo_order.move_byproduct_ids.product_id, bp1 + bp3 + bp4)

    def test_bom_never_attribute_mix(self):
        color, size = self.env["product.attribute"].create(
            [
                {
                    "name": name,
                    "display_type": "multi",
                    "create_variant": "no_variant",
                }
                for name in ["color", "size"]
            ]
        )

        self.env["product.attribute.value"].create(
            [
                {
                    "name": "Meh",
                    "attribute_id": attribute.id,
                }
                for attribute in [color, size]
            ]
        )

        tmpl_attr_line_color, tmpl_attr_line_size = self.env[
            "product.template.attribute.line"
        ].create(
            [
                {
                    "attribute_id": attribute.id,
                    "product_tmpl_id": self.product_1.product_tmpl_id.id,
                    "value_ids": [Command.set(attribute.value_ids.ids)],
                }
                for attribute in [color, size]
            ]
        )

        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_1.product_tmpl_id.id,
                "product_uom_id": self.product_1.product_tmpl_id.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_2.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    tmpl_attr_line_color.product_template_value_ids[
                                        0
                                    ].id
                                ),
                            ],
                        }
                    ),
                ],
            }
        )
        order = self.env["mrp.production"].create(
            {
                "product_id": self.product_1.id,
                "bom_id": bom.id,
                "never_product_template_attribute_value_ids": [
                    Command.link(tmpl_attr_line_size.product_template_value_ids[0].id),
                ],
            }
        )
        self.assertEqual(len(order.move_raw_ids), 0, "No component should be selected")

    def test_workorders_on_bom_changes(self):
        product = self.product_4
        bom_1, bom_2, bom_3 = self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "operation_ids": [
                        Command.create(
                            {
                                "name": "op1",
                                "workcenter_id": self.workcenter_1.id,
                                "time_cycle": 1.0,
                            }
                        ),
                        Command.create(
                            {
                                "name": "op2",
                                "workcenter_id": self.workcenter_1.id,
                                "time_cycle": 1.0,
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "operation_ids": [
                        Command.create(
                            {
                                "name": "op3",
                                "workcenter_id": self.workcenter_1.id,
                                "time_cycle": 1.0,
                            }
                        ),
                        Command.create(
                            {
                                "name": "op4",
                                "workcenter_id": self.workcenter_1.id,
                                "time_cycle": 1.0,
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "product_qty": 1.0,
                    "operation_ids": [
                        Command.create(
                            {
                                "name": "op5",
                                "workcenter_id": self.workcenter_1.id,
                                "time_cycle": 1.0,
                            }
                        ),
                        Command.create(
                            {
                                "name": "op6",
                                "workcenter_id": self.workcenter_1.id,
                                "time_cycle": 1.0,
                            }
                        ),
                    ],
                },
            ]
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = product
        mo_form.product_qty = 1.0
        mo_form.bom_id = bom_1
        mo = mo_form.save()
        self.assertEqual(mo.workorder_ids.mapped("name"), ["op1", "op2"])
        with Form(mo) as mo_form:
            mo_form.bom_id = bom_2
        self.assertEqual(mo.workorder_ids.mapped("name"), ["op3", "op4"])
        with Form(mo) as mo_form:
            mo_form.bom_id = bom_1
            mo_form.bom_id = bom_3
        self.assertEqual(mo.workorder_ids.mapped("name"), ["op5", "op6"])
        with Form(mo) as mo_form:
            with mo_form.workorder_ids.new() as wo_form:
                wo_form.name = "new op"
                wo_form.workcenter_id = self.workcenter_2
        self.assertEqual(mo.workorder_ids.mapped("name"), ["op5", "op6", "new op"])
        with Form(mo) as mo_form:
            mo_form.bom_id = bom_2
        self.assertEqual(set(mo.workorder_ids.mapped("name")), {"op3", "op4", "new op"})

    def test_archive_operation(self):
        final, comp1, comp2, bp1, bp2 = self.make_prods(5)
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": final.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": comp1.id, "product_qty": 1.0}),
                    Command.create({"product_id": comp2.id, "product_qty": 1.0}),
                ],
                "byproduct_ids": [
                    Command.create({"product_id": bp1.id, "product_qty": 1.0}),
                    Command.create({"product_id": bp2.id, "product_qty": 1.0}),
                ],
                "operation_ids": [
                    Command.create(
                        {"name": "OPE_1", "workcenter_id": self.workcenter_1.id}
                    ),
                    Command.create(
                        {"name": "OPE_2", "workcenter_id": self.workcenter_1.id}
                    ),
                ],
            }
        )
        ope_1, ope_2 = bom.operation_ids
        bom.bom_line_ids[0].operation_id = ope_1
        bom.byproduct_ids[0].operation_id = ope_1
        bom.bom_line_ids[1].operation_id = ope_2
        bom.byproduct_ids[1].operation_id = ope_2

        ope_1.action_archive()
        self.assertFalse(bom.bom_line_ids[0].operation_id)
        self.assertFalse(bom.byproduct_ids[0].operation_id)
        self.assertEqual(bom.bom_line_ids[1].operation_id, ope_2)
        self.assertEqual(bom.byproduct_ids[1].operation_id, ope_2)

    def test_bom_overview_for_product_template_with_dynamic_variants(self):
        dynamic_attribute = self.env["product.attribute"].create(
            {
                "name": "Dynamic",
                "create_variant": "dynamic",
                "value_ids": [
                    Command.create({"name": "red", "sequence": 1}),
                ],
            }
        )
        attr_val = dynamic_attribute["value_ids"][0]
        product_with_dynamic_variant = self.env["product.template"].create(
            {
                "name": "John Cutter",
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": dynamic_attribute.id,
                            "value_ids": [attr_val.id],
                        }
                    )
                ],
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_with_dynamic_variant.id,
                "operation_ids": [
                    Command.create(
                        {
                            "name": "Rub it gently with a cloth two at once",
                            "workcenter_id": self.workcenter_3.id,
                        }
                    ),
                ],
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_1.id,
                        }
                    )
                ],
                "byproduct_ids": [
                    Command.create({"product_id": self.product_1.id}),
                ],
            }
        )
        bom_overview = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom.id
        )["lines"]
        self.assertTrue(bom_overview["byproducts"])
        self.assertFalse(bom_overview["product"])
        self.assertTrue(bom_overview["components"])

    def test_copy_bom_with_operations(self):
        bom = self.bom_2
        bom.bom_line_ids.operation_id = bom.operation_ids
        bom.byproduct_ids = [
            Command.create(
                {
                    "product_id": self.product_2.id,
                    "product_qty": 1,
                    "operation_id": bom.operation_ids.id,
                }
            )
        ]
        copied_bom = bom.copy()
        copied_operation = copied_bom.operation_ids
        self.assertEqual(len(copied_operation), 1)
        self.assertNotEqual(bom.operation_ids, copied_operation)
        self.assertEqual(copied_bom.bom_line_ids.operation_id, copied_operation)
        self.assertEqual(copied_bom.byproduct_ids.operation_id, copied_operation)
        copied_operation.action_archive()
        self.assertFalse(
            copied_bom.bom_line_ids.operation_id | copied_bom.byproduct_ids.operation_id
        )

    def test_bom_overview_forecasted_component_status(self):
        main_bom = self.make_bom(self.productA, self.productB)
        self.env["mrp.production"].create(
            {
                "product_id": self.productA.id,
                "product_qty": 1.0,
                "bom_id": main_bom.id,
                "date_start": fields.Datetime.now() + timedelta(days=10),
            }
        ).action_confirm()
        self.env["mrp.production"].create(
            {"product_id": self.productB.id, "product_qty": 2.0}
        ).action_confirm()

        comp_line = self._get_component_line(main_bom, self.productB)
        self.assertEqual(comp_line["availability_state"], "expected")
        self.assertFalse(comp_line.get("status"))

        comp_line = self._get_component_line(main_bom, self.productB, qty=2)
        self.assertEqual(comp_line["availability_state"], "unavailable")
        self.assertEqual(comp_line.get("status"), "1.00 To Order")

    def test_bom_with_operations_for_kit_variant(self):
        kit_product_template = self.product_7_template
        red, blue = kit_product_template.product_variant_ids[
            :2
        ].product_template_attribute_value_ids
        blue_sofa = kit_product_template.product_variant_ids.filtered(
            lambda p: p.product_template_attribute_value_ids == blue
        )
        kit_bom, test_bom = self.env["mrp.bom"].create(
            [
                {
                    "product_tmpl_id": kit_product_template.id,
                    "product_uom_id": kit_product_template.uom_id.id,
                    "product_qty": 1.0,
                    "type": "phantom",
                    "operation_ids": [
                        Command.create(
                            {
                                "name": "Paint it Red",
                                "workcenter_id": self.workcenter_1.id,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(red.id)
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "name": "Paint it Blue",
                                "workcenter_id": self.workcenter_1.id,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(blue.id)
                                ],
                            }
                        ),
                    ],
                },
                {
                    "product_tmpl_id": self.product.product_tmpl_id.id,
                    "product_uom_id": self.product.product_tmpl_id.uom_id.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "bom_line_ids": [
                        Command.create(
                            {
                                "product_id": blue_sofa.id,
                                "product_qty": 2,
                            }
                        ),
                    ],
                },
            ]
        )
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.product
        mo_form.product_qty = 1.0
        mo_form.bom_id = test_bom
        mo = mo_form.save()
        self.assertEqual(
            mo.workorder_ids.operation_id,
            kit_bom.operation_ids.filtered(
                lambda op: op.bom_product_template_attribute_value_ids == blue
            ),
        )

    def test_correct_bom_final_product_unit(self):
        final_product = self.env["product.product"].create(
            dict({"is_storable": True}, name="Product to manufacture")
        )
        final_product.tracking = "lot"
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = final_product
        mo_form.product_qty = 1
        mo_form.product_uom_id = self.uom_dozen
        mo = mo_form.save()
        mo.action_confirm()
        mo.button_mark_done()
        self.assertEqual(mo.finished_move_line_ids.product_uom_id, self.uom_dozen)

    def test_bom_overview_with_decimal_quantity(self):
        product_in_square_meter = self.env["product.template"].create(
            {
                "name": "test",
                "uom_id": self.env.ref("uom.product_uom_square_meter").id,
            }
        )
        workcenter = self.env["mrp.workcenter"].create(
            {
                "name": "workcenter",
            }
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_in_square_meter.id,
                "product_qty": 1.5,
                "operation_ids": [
                    Command.create(
                        {
                            "name": "operation",
                            "workcenter_id": workcenter.id,
                            "time_cycle_manual": 16,
                        }
                    ),
                ],
            }
        )
        bom_overview = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom.id, 1.4
        )["lines"]
        self.assertEqual(bom_overview["operations_time"], 16)
        bom_overview = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom.id, 1.5
        )["lines"]
        self.assertEqual(bom_overview["operations_time"], 16)
        bom_overview = self.env["report.mrp.report_bom_structure"]._get_report_data(
            bom.id, 1.6
        )["lines"]
        self.assertEqual(bom_overview["operations_time"], 32)


@tagged("-at_install", "post_install")
class TestTourBoM(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "test1",
                "is_storable": True,
            }
        )
        cls.bom = cls.env["mrp.bom"].create(
            {
                "product_id": cls.product.id,
                "product_tmpl_id": cls.product.product_tmpl_id.id,
                "product_qty": 1,
                "type": "normal",
            }
        )
        cls.component = cls.env["product.product"].create(
            {
                "name": "compo test",
                "is_storable": True,
            }
        )

    def test_mrp_bom_product_catalog(self):
        grp_uom = self.env.ref("uom.group_uom")
        group_user = self.env.ref("base.group_user")
        group_user.write({"implied_ids": [Command.link(grp_uom.id)]})
        self.env.user.write({"group_ids": [Command.link(grp_uom.id)]})
        self.assertEqual(len(self.bom.bom_line_ids), 0)

        url = f"/odoo/action-mrp.mrp_bom_form_action/{self.bom.id}"

        self.start_tour(url, "test_mrp_bom_product_catalog", login="admin")
        self.assertEqual(len(self.bom.bom_line_ids), 1)

    def test_manufacture_from_bom(self):
        url = "/odoo/action-mrp.mrp_bom_form_action"
        self.start_tour(url, "test_manufacture_from_bom", login="admin", timeout=100)

    def test_bom_kit_rounding(self):
        integer_unit = self.env["uom.uom"].create(
            {
                "name": "unit_int",
                "rounding": 1.0,
            }
        )
        prod, comp = self.env["product.product"].create(
            [{"name": name, "uom_id": integer_unit.id} for name in ["prod", "comp"]]
        )
        comp.is_storable = True

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": prod.product_tmpl_id.id,
                "product_uom_id": integer_unit.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": comp.id,
                            "product_qty": 2.0,
                        }
                    )
                ],
            }
        )

        location = self.env.ref("stock.stock_location_stock")
        self.env["stock.quant"]._update_available_quantity(comp, location, 3.0)
        self.assertEqual(prod.qty_available, 1.0)

    def test_byproduct_bom_cost_share_constraint_with_variants(self):
        attributes = self.env["product.attribute"].create(
            [{"name": name} for name in ("Size", "Color")]
        )
        attributes_values = (
            (attributes[0], ("S", "M")),
            (attributes[1], ("Blue", "Red")),
        )
        self.env["product.attribute.value"].create(
            [
                {"name": name, "attribute_id": attribute.id}
                for attribute, names in attributes_values
                for name in names
            ]
        )
        product_template = self.env["product.template"].create(
            {
                "name": "lovely product",
                "is_storable": True,
            }
        )
        size_attribute_lines, color_attribute_lines = self.env[
            "product.template.attribute.line"
        ].create(
            [
                {
                    "product_tmpl_id": product_template.id,
                    "attribute_id": attribute.id,
                    "value_ids": [Command.set(attribute.value_ids.ids)],
                }
                for attribute in attributes
            ]
        )
        self.assertEqual(product_template.product_variant_count, 4)
        c1, c2, c3 = self.env["product.product"].create(
            [{"name": f"Comp {i}"} for i in range(1, 4)]
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "byproduct_ids": [
                    Command.create(
                        {"product_id": c1.id, "product_qty": 1, "cost_share": 100}
                    ),
                    Command.create(
                        {"product_id": c2.id, "product_qty": 0, "cost_share": 100}
                    ),
                ],
            }
        )

        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 30,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        0
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 15,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        1
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c2.id,
                            "product_qty": 1,
                            "cost_share": 15,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        1
                                    ].id
                                )
                            ],
                        }
                    ),
                    Command.create(
                        {"product_id": c2.id, "product_qty": 1, "cost_share": 70}
                    ),
                ],
            }
        )

        with self.assertRaises(UserError):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": product_template.id,
                    "product_uom_id": product_template.uom_id.id,
                    "product_qty": 1.0,
                    "type": "normal",
                    "byproduct_ids": [
                        Command.create(
                            {
                                "product_id": c1.id,
                                "product_qty": 1,
                                "cost_share": 30,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(
                                        size_attribute_lines.product_template_value_ids[
                                            1
                                        ].id
                                    ),
                                ],
                            }
                        ),
                        Command.create(
                            {
                                "product_id": c2.id,
                                "product_qty": 1,
                                "cost_share": 30,
                                "bom_product_template_attribute_value_ids": [
                                    Command.link(
                                        color_attribute_lines.product_template_value_ids[
                                            0
                                        ].id
                                    ),
                                ],
                            }
                        ),
                        Command.create(
                            {"product_id": c3.id, "product_qty": 1, "cost_share": 70}
                        ),
                    ],
                }
            )
        product_template.product_variant_ids[1:3].action_archive()
        self.assertEqual(product_template.product_variant_count, 2)
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": product_template.id,
                "product_uom_id": product_template.uom_id.id,
                "product_qty": 1.0,
                "type": "normal",
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": c1.id,
                            "product_qty": 1,
                            "cost_share": 30,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    size_attribute_lines.product_template_value_ids[
                                        1
                                    ].id
                                ),
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "product_id": c2.id,
                            "product_qty": 1,
                            "cost_share": 30,
                            "bom_product_template_attribute_value_ids": [
                                Command.link(
                                    color_attribute_lines.product_template_value_ids[
                                        0
                                    ].id
                                ),
                            ],
                        }
                    ),
                    Command.create(
                        {"product_id": c3.id, "product_qty": 1, "cost_share": 70}
                    ),
                ],
            }
        )


class TestBoMComponentChatter(TestMrpCommon):
    def setUp(self):
        super().setUp()
        self.env = self.env(
            context={
                **self.env.context,
                "tracking_disable": False,
                "mail_notrack": False,
            }
        )
        self.bom_1 = self.bom_1.with_env(self.env)
        self.bom_2 = self.bom_2.with_env(self.env)

    def _get_new_messages(self, bom, before):
        return bom.message_ids - before

    def test_write_tracked_field_logs_one_note(self):
        bom = self.bom_1
        line = bom.bom_line_ids.filtered(lambda l: l.product_id == self.product_2)
        before = bom.message_ids

        line.product_qty = 5.0

        message = self._get_new_messages(bom, before)
        self.assertEqual(len(message), 1)
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_note"))
        body = str(message.body)
        self.assertIn(self.product_2.display_name, body)
        self.assertIn(
            "{} → {}".format(
                float_repr(
                    2.0, self.env["decimal.precision"].get_precision("Product Unit")
                ),
                float_repr(
                    5.0, self.env["decimal.precision"].get_precision("Product Unit")
                ),
            ),
            body,
        )

    def test_write_reports_every_changed_field(self):
        bom = self.bom_1
        line = bom.bom_line_ids.filtered(lambda l: l.product_id == self.product_2)
        before = bom.message_ids

        line.write({"product_id": self.product_3.id, "product_qty": 7.0})

        body = str(self._get_new_messages(bom, before).body)
        self.assertIn(self.product_2.display_name, body)
        self.assertIn(self.product_3.display_name, body)
        self.assertIn("Quantity", body)

    def test_write_untracked_field_is_silent(self):
        bom = self.bom_1
        before = bom.message_ids

        bom.bom_line_ids[0].sequence = 42

        self.assertFalse(self._get_new_messages(bom, before))

    def test_write_without_a_real_change_is_silent(self):
        bom = self.bom_1
        line = bom.bom_line_ids[0]
        before = bom.message_ids

        line.product_qty = line.product_qty

        self.assertFalse(self._get_new_messages(bom, before))

    def test_write_across_boms_posts_to_each_thread(self):
        lines = self.bom_1.bom_line_ids[0] | self.bom_2.bom_line_ids[0]
        before_1, before_2 = self.bom_1.message_ids, self.bom_2.message_ids

        lines.product_qty = 9.0

        self.assertEqual(len(self._get_new_messages(self.bom_1, before_1)), 1)
        self.assertEqual(len(self._get_new_messages(self.bom_2, before_2)), 1)

    def test_unlink_logs_the_removed_component(self):
        bom = self.bom_1
        line = bom.bom_line_ids.filtered(lambda l: l.product_id == self.product_2)
        before = bom.message_ids

        line.unlink()

        message = self._get_new_messages(bom, before)
        self.assertEqual(len(message), 1)
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_note"))
        body = str(message.body)
        self.assertIn(self.product_2.display_name, body)
        self.assertIn("Components removed", body)

    def test_deleting_the_whole_bom_posts_nothing(self):
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_4.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": self.product_2.id, "product_qty": 1}),
                ],
            }
        )
        bom_id = bom.id
        bom.unlink()

        self.assertFalse(
            self.env["mail.message"].search_count(
                [("model", "=", "mrp.bom"), ("res_id", "=", bom_id)]
            )
        )

    def test_o2m_update_command_posts(self):
        bom = self.bom_1
        line = bom.bom_line_ids.filtered(lambda l: l.product_id == self.product_2)
        before = bom.message_ids

        bom.write({"bom_line_ids": [Command.update(line.id, {"product_qty": 6.0})]})

        message = self._get_new_messages(bom, before)
        self.assertEqual(len(message), 1)
        self.assertIn(self.product_2.display_name, str(message.body))

    def test_o2m_delete_command_posts(self):
        bom = self.bom_1
        line = bom.bom_line_ids.filtered(lambda l: l.product_id == self.product_2)
        before = bom.message_ids

        bom.write({"bom_line_ids": [Command.delete(line.id)]})

        body = str(self._get_new_messages(bom, before).body)
        self.assertIn("Components removed", body)
        self.assertIn(self.product_2.display_name, body)

    def test_restamping_the_unit_from_the_product_is_silent(self):
        component = self.env["product.product"].create(
            {"name": "Restamped component", "uom_id": self.uom_unit.id}
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self.product_4.product_tmpl_id.id,
                "product_qty": 1.0,
                "bom_line_ids": [
                    Command.create({"product_id": component.id, "product_qty": 3}),
                ],
            }
        )
        before = bom.message_ids

        component.product_tmpl_id.uom_id = self.uom_dozen

        self.assertEqual(bom.bom_line_ids.product_uom_id, self.uom_dozen)
        self.assertFalse(self._get_new_messages(bom, before))

    def test_the_frameworks_tracking_switches_are_honoured(self):
        bom = self.bom_1
        line = bom.bom_line_ids[0]
        before = bom.message_ids

        line.with_context(tracking_disable=True).product_qty = 11.0
        line.with_context(mail_notrack=True).product_qty = 12.0
        line.with_context(mail_notrack=True).unlink()

        self.assertFalse(self._get_new_messages(bom, before))


@tagged("post_install", "-at_install")
class TestBoMAuditFixes(TestMrpCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.unit = cls.env.ref("uom.product_uom_unit")
        cls.kg = cls.env.ref("uom.product_uom_kgm")
        cls.gram = cls.env.ref("uom.product_uom_gram")

    def _product(self, name, uom=None):
        return self.env["product.product"].create(
            {
                "name": name,
                "is_storable": True,
                "type": "consu",
                "uom_id": (uom or self.unit).id,
            }
        )

    def _bom_with_three_operations(self):
        finished = self._product("COPY-FIN")
        workcenter = self.env["mrp.workcenter"].search([], limit=1)
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "operation_ids": [
                    Command.create(
                        {
                            "name": f"Op{i}",
                            "workcenter_id": workcenter.id,
                            "sequence": 100 - i * 10,
                        }
                    )
                    for i in range(3)
                ],
                "bom_line_ids": [
                    Command.create(
                        {"product_id": self._product(f"COPY-C{i}").id, "product_qty": 1}
                    )
                    for i in range(2)
                ],
                "byproduct_ids": [
                    Command.create(
                        {"product_id": self._product("COPY-BP").id, "product_qty": 1}
                    )
                ],
            }
        )
        operations = {operation.name: operation for operation in bom.operation_ids}
        bom.bom_line_ids[0].operation_id = operations["Op0"]
        bom.bom_line_ids[1].operation_id = operations["Op2"]
        bom.byproduct_ids[0].operation_id = operations["Op1"]
        operations["Op0"].blocked_by_operation_ids = [
            Command.set(operations["Op2"].ids)
        ]
        return bom

    def _assert_copy_is_faithful(self, bom, copied):
        for old, new in zip(bom.bom_line_ids, copied.bom_line_ids, strict=True):
            self.assertEqual(old.operation_id.name, new.operation_id.name)
        for old, new in zip(bom.byproduct_ids, copied.byproduct_ids, strict=True):
            self.assertEqual(old.operation_id.name, new.operation_id.name)
        self.assertEqual(
            {
                op.name: sorted(op.blocked_by_operation_ids.mapped("name"))
                for op in bom.operation_ids
            },
            {
                op.name: sorted(op.blocked_by_operation_ids.mapped("name"))
                for op in copied.operation_ids
            },
        )

    def test_copy_keeps_operations_paired_with_a_cold_cache(self):
        bom = self._bom_with_three_operations()
        self.env.flush_all()
        self.env.invalidate_all()
        bom = bom.browse(bom.id)
        self._assert_copy_is_faithful(bom, bom.copy())

    def test_copy_keeps_operations_paired_with_a_warm_cache(self):
        bom = self._bom_with_three_operations()
        self._assert_copy_is_faithful(bom, bom.copy())

    def test_copy_of_a_copy_keeps_operations_paired(self):
        bom = self._bom_with_three_operations()
        self.env.flush_all()
        self.env.invalidate_all()
        first = bom.browse(bom.id).copy()
        self._assert_copy_is_faithful(first, first.copy())

    def test_batch_copy_keeps_every_bom_paired(self):
        cold = self._bom_with_three_operations()
        self.env.flush_all()
        self.env.invalidate_all()
        cold = cold.browse(cold.id)
        warm = self._bom_with_three_operations()
        sources = cold | warm
        copies = sources.copy()
        for source, copied in zip(sources, copies, strict=True):
            self._assert_copy_is_faithful(source, copied)

    def test_cycle_check_is_linear_in_a_shared_component_graph(self):
        below = [self._product(f"LADDER-leaf{j}") for j in range(2)]
        levels = 14
        for i in reversed(range(levels)):
            current = [self._product(f"LADDER-L{i}-{j}") for j in range(2)]
            for product in current:
                self.env["mrp.bom"].with_context(
                    skip_bom_cycle_check=True
                ).sudo().create(
                    {
                        "product_tmpl_id": product.product_tmpl_id.id,
                        "bom_line_ids": [
                            Command.create({"product_id": c.id, "product_qty": 1})
                            for c in below
                        ],
                    }
                )
            below = current
        bom = self.env["mrp.bom"].search(
            [("product_tmpl_id", "=", below[0].product_tmpl_id.id)], limit=1
        )
        self.env.invalidate_all()
        start = fields.Datetime.now()
        bom._check_bom_cycle()
        self.assertLess(
            (fields.Datetime.now() - start).total_seconds(),
            20,
            "the cycle check walked paths instead of nodes",
        )

    def test_cycle_check_sees_a_bom_that_is_not_the_selected_one(self):
        products = {
            name: self._product(f"SEL-{name}") for name in ("R", "C", "M", "F", "L")
        }
        Bom = self.env["mrp.bom"]

        def make(finished, component, sequence):
            return Bom.create(
                {
                    "product_tmpl_id": products[finished].product_tmpl_id.id,
                    "sequence": sequence,
                    "bom_line_ids": [
                        Command.create(
                            {"product_id": products[component].id, "product_qty": 1}
                        )
                    ],
                }
            )

        make("R", "C", 5)
        make("C", "M", 5)
        make("M", "F", 5)
        make("F", "L", 1)
        with self.assertRaises(exceptions.ValidationError):
            make("F", "C", 99)

    def test_display_name_follows_the_quantity_and_the_unit(self):
        product = self._product("DN-P")
        bom = (
            self.env["mrp.bom"]
            .with_context(display_bom_uom_qty=True)
            .create({"product_tmpl_id": product.product_tmpl_id.id, "product_qty": 5.0})
        )
        self.assertIn("(5.0 Units)", bom.display_name)
        bom.product_qty = 11.0
        self.assertIn("(11.0 Units)", bom.display_name)

    def test_display_name_is_cached_per_context(self):
        product = self._product("DN-CTX")
        bom = self.env["mrp.bom"].create(
            {"product_tmpl_id": product.product_tmpl_id.id, "product_qty": 5.0}
        )
        self.assertNotIn("(5.0 Units)", bom.display_name)
        self.assertIn(
            "(5.0 Units)", bom.with_context(display_bom_uom_qty=True).display_name
        )

    def test_the_orderpoint_list_shows_the_bom_quantity(self):
        product = self._product("DN-OP")
        bom = self.env["mrp.bom"].create(
            {"product_tmpl_id": product.product_tmpl_id.id, "product_qty": 5.0}
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "bom_id": bom.id,
            }
        )
        self.env.flush_all()
        self.env.invalidate_all()
        record = self.env["stock.warehouse.orderpoint"].web_search_read(
            [("id", "=", orderpoint.id)],
            {
                "bom_id_placeholder": {},
                "bom_id": {
                    "context": {"display_bom_uom_qty": True},
                    "fields": {"display_name": {}},
                },
            },
        )["records"][0]
        self.assertIn("(5.0 Units)", record["bom_id"]["display_name"])

    def test_set_bom_button_is_hidden_for_the_bom_already_set(self):
        product = self._product("SB-P")
        bom = self.env["mrp.bom"].create(
            {"product_tmpl_id": product.product_tmpl_id.id}
        )
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "bom_id": bom.id,
            }
        )
        self.assertTrue(bom.show_set_bom_button)
        self.assertFalse(
            bom.with_context(orderpoint_id=orderpoint.id).show_set_bom_button
        )

    def test_catalog_quantity_is_summed_in_the_products_own_unit(self):
        flour = self._product("CAT-FLOUR", self.kg)
        cake = self._product("CAT-CAKE")
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": cake.product_tmpl_id.id,
                "bom_line_ids": [
                    Command.create(
                        {
                            "product_id": flour.id,
                            "product_qty": 1.0,
                            "product_uom_id": self.kg.id,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": flour.id,
                            "product_qty": 500.0,
                            "product_uom_id": self.gram.id,
                        }
                    ),
                ],
            }
        )
        data = bom.bom_line_ids._get_product_catalog_lines_data()
        self.assertEqual(data["quantity"], 1.5, "1 kg + 500 g is 1.5 kg, not 501")

    def test_catalog_default_payload_comes_from_an_empty_recordset(self):
        bom = self.env["mrp.bom"].create(
            {"product_tmpl_id": self._product("CAT-D").product_tmpl_id.id}
        )
        self.assertEqual(bom._get_order_line_values("bom_line_ids")["quantity"], 0)

    def test_a_byproduct_quantity_cannot_be_negative(self):
        finished = self._product("NEG-F")
        with self.assertRaises(Exception):
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": finished.product_tmpl_id.id,
                    "byproduct_ids": [
                        Command.create(
                            {
                                "product_id": self._product("NEG-B").id,
                                "product_qty": -5.0,
                            }
                        )
                    ],
                }
            )
            self.env.flush_all()

    def test_a_byproduct_cost_share_of_zero_is_allowed(self):
        finished = self._product("CS0-F")
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": finished.product_tmpl_id.id,
                "byproduct_ids": [
                    Command.create(
                        {
                            "product_id": self._product("CS0-B").id,
                            "product_qty": 1.0,
                            "cost_share": 0,
                        }
                    )
                ],
            }
        )
        self.assertEqual(bom.byproduct_ids.cost_share, 0)

    def test_create_links_every_bom_to_the_parent_production(self):
        cake = self._product("PP-CAKE")
        production = self.env["mrp.production"].create(
            {"product_id": cake.id, "product_qty": 1}
        )
        boms = (
            self.env["mrp.bom"]
            .with_context(parent_production_id=production.id)
            .create(
                [
                    {"product_tmpl_id": self._product("PP-A").product_tmpl_id.id},
                    {"product_tmpl_id": self._product("PP-B").product_tmpl_id.id},
                ]
            )
        )
        self.assertEqual(len(boms), 2)
        self.assertEqual(production.bom_id, boms[-1])

    def test_create_does_not_write_into_the_callers_vals(self):
        vals = {"product_tmpl_id": self._product("VM-P").product_tmpl_id.id}
        snapshot = dict(vals)
        self.env["mrp.bom"].create([vals])
        self.assertEqual(vals, snapshot)

    def test_name_create_returns_the_label_it_stored(self):
        template = self._product("NC-P").product_tmpl_id
        bom_id, label = (
            self.env["mrp.bom"]
            .with_context(default_product_tmpl_id=template.id)
            .name_create("MY-REF")
        )
        bom = self.env["mrp.bom"].browse(bom_id)
        self.assertEqual(bom.code, "MY-REF")
        self.assertEqual(label, bom.display_name)
        self.assertIn("MY-REF", label)

    def test_changing_the_product_keeps_a_typed_reference(self):
        first = self._product("REF-A")
        second = self._product("REF-B")
        self.env["mrp.bom"].create({"product_tmpl_id": second.product_tmpl_id.id})
        form = Form(self.env["mrp.bom"])
        form.product_tmpl_id = first.product_tmpl_id
        form.code = "MY-OWN-REF"
        form.product_tmpl_id = second.product_tmpl_id
        self.assertEqual(form.code, "MY-OWN-REF")

    def test_unarchiving_a_bom_leaves_a_retired_operation_retired(self):
        workcenter = self.env["mrp.workcenter"].search([], limit=1)
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": self._product("ARCH-F").product_tmpl_id.id,
                "operation_ids": [
                    Command.create({"name": "Keep", "workcenter_id": workcenter.id}),
                    Command.create({"name": "Retired", "workcenter_id": workcenter.id}),
                ],
            }
        )
        bom.operation_ids.filtered(lambda o: o.name == "Retired").action_archive()
        self.assertEqual(bom.operation_ids.mapped("name"), ["Keep"])
        bom.action_archive()
        bom.action_unarchive()
        self.assertEqual(bom.operation_ids.mapped("name"), ["Keep"])

    def test_an_order_on_an_archived_variant_is_still_flagged(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "ARCH-SIZE",
                "create_variant": "always",
                "value_ids": [
                    Command.create({"name": "s"}),
                    Command.create({"name": "m"}),
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": "ARCH-TMPL",
                "type": "consu",
                "is_storable": True,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(attribute.value_ids.ids)],
                        }
                    )
                ],
            }
        )
        kept, archived = (
            template.product_variant_ids[0],
            template.product_variant_ids[1],
        )
        bom = self.env["mrp.bom"].create(
            {
                "product_tmpl_id": template.id,
                "bom_line_ids": [
                    Command.create(
                        {"product_id": self._product("ARCH-C").id, "product_qty": 1}
                    )
                ],
            }
        )
        orders = {}
        for label, variant in (("kept", kept), ("archived", archived)):
            order = self.env["mrp.production"].create(
                {"product_id": variant.id, "product_qty": 1, "bom_id": bom.id}
            )
            order.action_confirm()
            order.is_outdated_bom = False
            orders[label] = order
        self.env.flush_all()
        archived.active = False
        self.env.flush_all()
        bom.write({"product_qty": 3.0})
        self.assertTrue(orders["kept"].is_outdated_bom)
        self.assertTrue(
            orders["archived"].is_outdated_bom,
            "an order on an archived variant matched neither domain",
        )

    def test_child_bom_id_is_scoped_to_the_boms_company(self):
        other_company = self.env["res.company"].create({"name": "CHILD-CO2"})
        shared = self._product("CHILD-SHARED")
        Bom = self.env["mrp.bom"]
        mine = Bom.create(
            {
                "product_tmpl_id": shared.product_tmpl_id.id,
                "company_id": self.env.company.id,
                "sequence": 20,
            }
        )
        Bom.create(
            {
                "product_tmpl_id": shared.product_tmpl_id.id,
                "company_id": other_company.id,
                "sequence": 10,
            }
        )
        parent = Bom.create(
            {
                "product_tmpl_id": self._product("CHILD-TOP").product_tmpl_id.id,
                "company_id": self.env.company.id,
                "bom_line_ids": [
                    Command.create({"product_id": shared.id, "product_qty": 1})
                ],
            }
        )
        parent.bom_line_ids.invalidate_recordset()
        self.assertEqual(parent.bom_line_ids.child_bom_id, mine)

    def test_one_skip_rule_serves_lines_byproducts_and_operations(self):
        mixin = type(self.env["mixin.bom.variant.line"])
        for model in ("mrp.bom.line", "mrp.bom.byproduct"):
            self.assertIs(
                type(self.env[model])._is_bom_line_skipped,
                mixin._is_bom_line_skipped,
                f"{model} should inherit the shared rule, not carry a copy",
            )
        operation = type(self.env["mrp.routing.workcenter"])._is_bom_line_skipped
        self.assertIsNot(operation, mixin._is_bom_line_skipped)
        for model in ("mrp.bom.line", "mrp.bom.byproduct", "mrp.routing.workcenter"):
            fields = self.env[model]._fields
            self.assertIn("bom_product_template_attribute_value_ids", fields)
            self.assertIn("possible_bom_product_template_attribute_value_ids", fields)

    def test_explode_resolves_the_kit_closure_level_by_level(self):

        def kit(depth, width, tag):
            product = self._product(f"{tag}-d{depth}")
            if depth == 0:
                return product
            children = [kit(depth - 1, width, f"{tag}-{i}") for i in range(width)]
            self.env["mrp.bom"].create(
                {
                    "product_tmpl_id": product.product_tmpl_id.id,
                    "type": "phantom",
                    "bom_line_ids": [
                        Command.create({"product_id": c.id, "product_qty": 1})
                        for c in children
                    ],
                }
            )
            return product

        root = kit(3, 3, "KIT")
        bom = self.env["mrp.bom"]._get_bom_by_product(root, bom_type="phantom")[root]
        self.env.invalidate_all()
        searches = []
        original = type(self.env["mrp.bom"])._get_bom_by_product

        def counting(model, products, **kwargs):
            searches.append(len(products))
            return original(model, products, **kwargs)

        type(self.env["mrp.bom"])._get_bom_by_product = counting
        try:
            _boms, lines = bom._explode(root, 1.0)
        finally:
            type(self.env["mrp.bom"])._get_bom_by_product = original
        self.assertEqual(len(lines), 27)
        self.assertLessEqual(
            len(searches), 4, "one _get_bom_by_product per level, not one per node"
        )

    def test_explode_skips_restricted_lines_without_resolving_them(self):
        attribute = self.env["product.attribute"].create(
            {
                "name": "EXP-OPT",
                "create_variant": "no_variant",
                "value_ids": [Command.create({"name": "on"})],
            }
        )
        finished = self._product("EXP-F")
        template = finished.product_tmpl_id
        template.attribute_line_ids = [
            Command.create(
                {
                    "attribute_id": attribute.id,
                    "value_ids": [Command.set(attribute.value_ids.ids)],
                }
            )
        ]
        ptav = template.valid_product_template_attribute_line_ids.product_template_value_ids
        kept = self._product("EXP-KEPT")
        skipped = self._product("EXP-SKIPPED")
        self.env["mrp.bom"].create(
            {
                "product_tmpl_id": template.id,
                "type": "phantom",
                "bom_line_ids": [
                    Command.create({"product_id": kept.id, "product_qty": 1}),
                    Command.create(
                        {
                            "product_id": skipped.id,
                            "product_qty": 1,
                            "bom_product_template_attribute_value_ids": [
                                Command.set(ptav.ids)
                            ],
                        }
                    ),
                ],
            }
        )
        variant = template.product_variant_ids[0]
        bom = self.env["mrp.bom"]._get_bom_by_product(variant, bom_type="phantom")[
            variant
        ]
        _boms, lines = bom._explode(variant, 1.0)
        self.assertEqual([line.product_id for line, _vals in lines], [kept])

    def _variant_pair(self, tag):
        attribute = self.env["product.attribute"].create(
            {
                "name": f"{tag}-A",
                "create_variant": "always",
                "value_ids": [
                    Command.create({"name": "x"}),
                    Command.create({"name": "y"}),
                ],
            }
        )
        template = self.env["product.template"].create(
            {
                "name": f"{tag}-T",
                "type": "consu",
                "is_storable": True,
                "attribute_line_ids": [
                    Command.create(
                        {
                            "attribute_id": attribute.id,
                            "value_ids": [Command.set(attribute.value_ids.ids)],
                        }
                    )
                ],
            }
        )
        return template, template.product_variant_ids

    def test_bom_find_prefers_the_variant_bom_at_equal_sequence(self):
        template, (first, second) = self._variant_pair("TIE1")
        Bom = self.env["mrp.bom"]
        variant_bom = Bom.create(
            {"product_tmpl_id": template.id, "product_id": first.id, "sequence": 5}
        )
        template_bom = Bom.create({"product_tmpl_id": template.id, "sequence": 5})
        found = Bom._get_bom_by_product(first | second)
        self.assertEqual(found[first], variant_bom)
        self.assertEqual(found[second], template_bom)

    def test_bom_find_lets_a_lower_sequence_template_bom_win(self):
        template, (first, second) = self._variant_pair("TIE2")
        Bom = self.env["mrp.bom"]
        Bom.create(
            {"product_tmpl_id": template.id, "product_id": first.id, "sequence": 10}
        )
        template_bom = Bom.create({"product_tmpl_id": template.id, "sequence": 5})
        found = Bom._get_bom_by_product(first | second)
        self.assertEqual(found[first], template_bom)
        self.assertEqual(found[second], template_bom)

    def test_bom_find_agrees_with_itself_one_product_at_a_time(self):
        template, variants = self._variant_pair("TIE3")
        Bom = self.env["mrp.bom"]
        Bom.create(
            {
                "product_tmpl_id": template.id,
                "product_id": variants[0].id,
                "sequence": 7,
            }
        )
        Bom.create({"product_tmpl_id": template.id, "sequence": 3})
        Bom.create(
            {
                "product_tmpl_id": template.id,
                "product_id": variants[1].id,
                "sequence": 1,
            }
        )
        batch = Bom._get_bom_by_product(variants)
        for variant in variants:
            self.assertEqual(
                batch[variant],
                Bom._get_bom_by_product(variant)[variant],
                f"the two paths disagree for {variant.display_name}",
            )
