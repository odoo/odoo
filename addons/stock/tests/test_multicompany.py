from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, TransactionCase


class TestCompanyProvisioning(TransactionCase):
    def _inventory_default_field(self):
        return self.env["ir.model.fields"]._get(
            "product.template", "property_stock_inventory"
        )

    def test_companies_with_property_counts_per_company_default(self):
        company = self.env["res.company"].create({"name": "Prov Co"})
        having = self.env["res.company"]._get_companies_with_property(
            "product.template", "property_stock_inventory"
        )
        self.assertIn(
            company,
            having,
            "a company created with a per-company inventory default must be "
            "reported as already provisioned",
        )

    def test_companies_with_property_treats_global_default_as_all(self):
        company = self.env["res.company"].create({"name": "Prov Co"})
        field = self._inventory_default_field()
        self.env["ir.default"].sudo().search([("field_id", "=", field.id)]).unlink()
        loc = self.env["stock.location"].search(
            [("usage", "=", "inventory"), ("company_id", "=", company.id)], limit=1
        )
        self.env["ir.default"].set(
            "product.template",
            "property_stock_inventory",
            loc.id,
            company_id=False,
        )
        having = self.env["res.company"]._get_companies_with_property(
            "product.template", "property_stock_inventory"
        )
        self.assertEqual(
            having,
            self.env["res.company"].search([]),
            "a global default must mark all companies as provisioned",
        )
        self.assertFalse(
            self.env["res.company"]._get_companies_without(having),
            "no company should be considered missing the property",
        )

    def test_create_missing_skips_company_covered_by_global_default(self):
        company = self.env["res.company"].create({"name": "Prov Co"})
        field = self._inventory_default_field()
        self.env["ir.default"].sudo().search([("field_id", "=", field.id)]).unlink()
        domain = [("usage", "=", "inventory"), ("company_id", "=", company.id)]
        loc = self.env["stock.location"].search(domain, limit=1)
        self.env["ir.default"].set(
            "product.template",
            "property_stock_inventory",
            loc.id,
            company_id=False,
        )
        before = self.env["stock.location"].search_count(domain)
        self.env["res.company"].create_missing_inventory_loss_location()
        after = self.env["stock.location"].search_count(domain)
        self.assertEqual(
            after,
            before,
            "backfill duplicated an inventory-loss location despite a global "
            "default already covering the company",
        )

    def test_backfill_covers_archived_company(self):
        company = self.env["res.company"].create({"name": "Archived Co"})
        company.stock_config_id.internal_transit_location_id = False
        company.active = False
        self.assertIn(
            company,
            self.env["res.company"]._get_all_companies(),
            "archived companies must be visible to the backfill enumeration",
        )
        self.env["res.company"].create_missing_transit_location()
        company.invalidate_recordset()
        self.assertTrue(
            company.stock_config_id.internal_transit_location_id,
            "an archived company without a transit location must still be backfilled",
        )


class TestCompanyStockProvisioning(TransactionCase):
    def test_create_provisions_locations_sequence_and_partner(self):
        company = self.env["res.company"].create({"name": "Prov Co"})
        self.assertTrue(
            company.stock_config_id.internal_transit_location_id,
            "create() must provision a transit location",
        )
        default = self.env["ir.default"]
        self.assertTrue(
            default._get(
                "product.template", "property_stock_inventory", company_id=company.id
            ),
            "create() must register the inventory-loss location default",
        )
        self.assertTrue(
            default._get(
                "product.template", "property_stock_production", company_id=company.id
            ),
            "create() must register the production location default",
        )
        self.assertEqual(
            self.env["ir.sequence"].search_count(
                [("code", "=", "stock.scrap"), ("company_id", "=", company.id)]
            ),
            1,
            "create() must provision exactly one scrap sequence",
        )
        partner = company.partner_id.with_company(company)
        self.assertEqual(
            partner.property_stock_customer,
            company.stock_config_id.internal_transit_location_id,
            "the company partner's customer location must point at the transit location",
        )
        self.assertEqual(
            partner.property_stock_supplier,
            company.stock_config_id.internal_transit_location_id,
            "the company partner's supplier location must point at the transit location",
        )

    def test_set_stock_property_locations_helper(self):
        company = self.env["res.company"].create({"name": "Helper Co"})
        transit = company.stock_config_id.internal_transit_location_id
        partner = self.env["res.partner"].create({"name": "Prop Partner"})
        partner.with_company(company)._update_stock_property_locations(transit)
        self.assertEqual(partner.with_company(company).property_stock_customer, transit)
        self.assertEqual(partner.with_company(company).property_stock_supplier, transit)
        partner.with_company(company)._update_stock_property_locations(
            self.env["stock.location"]
        )
        self.assertFalse(partner.with_company(company).property_stock_customer)
        self.assertFalse(partner.with_company(company).property_stock_supplier)

    def test_create_missing_scrap_sequence_is_idempotent(self):
        self.env["res.company"].create({"name": "Scrap Co"})
        before = self.env["ir.sequence"].search_count([("code", "=", "stock.scrap")])
        self.env["res.company"].create_missing_scrap_sequence()
        after = self.env["ir.sequence"].search_count([("code", "=", "stock.scrap")])
        self.assertEqual(before, after, "backfill must not duplicate scrap sequences")

    def test_create_missing_transit_location_is_idempotent(self):
        self.env["res.company"].create({"name": "Transit Co"})
        self.env["res.company"].create_missing_transit_location()
        self.assertFalse(
            self.env["res.company"].search(
                [("stock_config_id.internal_transit_location_id", "=", False)]
            ),
            "every company must own a transit location and the backfill adds none twice",
        )

    def test_bootstrap_first_warehouse_is_noop_when_warehouse_exists(self):
        before = self.env["stock.warehouse"].search_count([])
        self.env["res.company"].create_missing_warehouse()
        self.assertEqual(
            self.env["stock.warehouse"].search_count([]),
            before,
            "create_missing_warehouse must not create a warehouse when one exists",
        )

    def test_get_text_validation_gate(self):
        company = self.env["res.company"].create({"name": "Text Co"})
        company.stock_config_id.stock_text_confirmation = True
        company.stock_config_id.stock_confirmation_type = "sms"
        self.assertTrue(company._is_text_confirmation_enabled("sms"))
        self.assertFalse(
            company._is_text_confirmation_enabled("whatsapp"),
            "a channel other than the configured one must not validate",
        )
        company.stock_config_id.stock_text_confirmation = False
        self.assertFalse(
            company._is_text_confirmation_enabled("sms"),
            "text confirmation disabled must never validate",
        )

    def test_horizon_days_rejects_negative(self):
        company = self.env["res.company"].create({"name": "Horizon Co"})
        with self.assertRaises(ValidationError):
            company.stock_config_id.horizon_days = -1

    def test_horizon_days_allows_zero(self):
        company = self.env["res.company"].create({"name": "Horizon Zero Co"})
        company.stock_config_id.horizon_days = 0
        self.assertEqual(company.stock_config_id.horizon_days, 0)

    def test_create_missing_mail_template_backfills_and_is_idempotent(self):
        template = self.env.ref("stock.mail_template_data_delivery_confirmation")
        active = self.env["res.company"].create({"name": "Tmpl Active"})
        archived = self.env["res.company"].create({"name": "Tmpl Archived"})
        (active + archived).stock_config_id.stock_mail_confirmation_template_id = False
        archived.active = False

        self.env["res.company"].create_missing_mail_template()

        self.assertEqual(
            active.stock_config_id.stock_mail_confirmation_template_id,
            template,
            "an active company without the template must be backfilled",
        )
        self.assertEqual(
            archived.stock_config_id.stock_mail_confirmation_template_id,
            template,
            "an archived company without the template must still be backfilled",
        )

        custom = template.copy({"name": "Custom Confirmation"})
        active.stock_config_id.stock_mail_confirmation_template_id = custom
        self.env["res.company"].create_missing_mail_template()
        self.assertEqual(
            active.stock_config_id.stock_mail_confirmation_template_id,
            custom,
            "the backfill must not overwrite a company's existing template",
        )


class TestMultiCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group_user = cls.env.ref("base.group_user")
        group_stock_manager = cls.env.ref("stock.group_stock_manager")

        cls.company_a = cls.env["res.company"].create({"name": "Company A"})
        cls.company_b = cls.env["res.company"].create({"name": "Company B"})
        cls.warehouse_a, cls.warehouse_b = (
            cls.company_a + cls.company_b
        )._create_warehouse()
        cls.stock_location_a = cls.warehouse_a.lot_stock_id
        cls.stock_location_b = cls.warehouse_b.lot_stock_id

        cls.user_a = cls.env["res.users"].create(
            {
                "name": "user company a with access to company b",
                "login": "user a",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            group_user.id,
                            group_stock_manager.id,
                        ],
                    )
                ],
                "company_id": cls.company_a.id,
                "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            }
        )
        cls.user_b = cls.env["res.users"].create(
            {
                "name": "user company b with access to company a",
                "login": "user b",
                "group_ids": [
                    (
                        6,
                        0,
                        [
                            group_user.id,
                            group_stock_manager.id,
                        ],
                    )
                ],
                "company_id": cls.company_b.id,
                "company_ids": [(6, 0, [cls.company_a.id, cls.company_b.id])],
            }
        )

    def test_orderpoint_lead_horizon_uses_own_company_horizon(self):
        self.company_a.stock_config_id.horizon_days = 10
        self.company_b.stock_config_id.horizon_days = 40
        product = self.env["product.product"].create(
            {"name": "horizon prod", "is_storable": True}
        )
        env_a = self.env(user=self.user_a)
        self.assertEqual(env_a.company, self.company_a)
        orderpoint = env_a["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "location_id": self.stock_location_b.id,
                "warehouse_id": self.warehouse_b.id,
                "company_id": self.company_b.id,
                "product_min_qty": 5.0,
                "product_max_qty": 10.0,
            }
        )
        offset = (orderpoint.lead_horizon_date - fields.Date.today()).days
        self.assertEqual(
            offset,
            40,
            "orderpoint should use company B's horizon (40), not env.company A's (10)",
        )

    def test_picking_type_1(self):
        picking_type_company_a = self.env["stock.picking.type"].search(
            [("company_id", "=", self.company_a.id)], limit=1
        )
        with self.assertRaises(UserError):
            picking_type_company_a.warehouse_id = self.warehouse_b

    def test_picking_type_2(self):
        picking_type_company_a = self.env["stock.picking.type"].search(
            [("company_id", "=", self.company_a.id)], limit=1
        )
        with self.assertRaises(UserError):
            picking_type_company_a.with_user(self.user_a).company_id = self.company_b

    def test_putaway_1(self):
        stock_location_a_1 = (
            self.env["stock.location"]
            .with_user(self.user_a)
            .create(
                {
                    "location_id": self.stock_location_a.id,
                    "usage": "internal",
                    "name": "A_1",
                }
            )
        )
        putaway_form = Form(self.env["stock.putaway.rule"])
        putaway_form.location_in_id = self.stock_location_a
        putaway_form.location_out_id = stock_location_a_1
        putaway_form.company_id = self.company_b
        with self.assertRaises(UserError):
            putaway_form.save()

    def test_putaway_2(self):
        stock_location_a_1 = (
            self.env["stock.location"]
            .with_user(self.user_a)
            .create(
                {
                    "name": "A_1",
                    "location_id": self.stock_location_a.id,
                    "usage": "internal",
                }
            )
        )
        putaway_rule = (
            self.env["stock.putaway.rule"]
            .with_user(self.user_a)
            .create(
                {
                    "location_in_id": self.stock_location_a.id,
                    "location_out_id": stock_location_a_1.id,
                }
            )
        )
        with self.assertRaises(UserError):
            putaway_rule.company_id = self.company_b

    def test_company_1(self):
        with self.assertRaises(UserError):
            self.company_a.stock_config_id.internal_transit_location_id = (
                self.company_b.stock_config_id.internal_transit_location_id
            )

    def test_partner_1(self):
        shared_partner = self.env["res.partner"].create(
            {
                "name": "Shared Partner",
                "company_id": False,
            }
        )
        with self.assertRaises(UserError):
            shared_partner.with_user(
                self.user_b
            ).property_stock_customer = self.stock_location_a

    def test_partner_2(self):
        inter_company_loc = self.env.ref("stock.stock_location_inter_company")
        self.assertEqual(
            self.company_a.partner_id.with_user(self.user_b).property_stock_customer,
            inter_company_loc,
        )
        self.assertEqual(
            self.company_a.partner_id.with_user(self.user_b).property_stock_supplier,
            inter_company_loc,
        )
        self.assertEqual(
            self.company_b.partner_id.with_user(self.user_a).property_stock_customer,
            inter_company_loc,
        )
        self.assertEqual(
            self.company_b.partner_id.with_user(self.user_a).property_stock_supplier,
            inter_company_loc,
        )

    def test_partner_3_intercompany_wiring_covers_archived_company(self):
        inter_company_loc = self.env.ref("stock.stock_location_inter_company")
        archived = self.env["res.company"].create({"name": "Archived Co"})
        archived.active = False

        fresh = self.env["res.company"].create({"name": "Fresh Co"})

        self.assertEqual(
            archived.partner_id.with_company(fresh).property_stock_customer,
            inter_company_loc,
            "the archived company must be wired toward the freshly created one",
        )
        self.assertEqual(
            fresh.partner_id.with_company(archived).property_stock_supplier,
            inter_company_loc,
            "the freshly created company must be wired toward the archived one",
        )

    def test_inventory_1(self):
        product = self.env["product.product"].create(
            {
                "is_storable": True,
                "company_id": self.company_a.id,
                "name": "Product limited to company A",
            }
        )
        inventory_quant = (
            self.env["stock.quant"]
            .with_user(self.user_a)
            .with_context(inventory_mode=True)
            .create(
                {
                    "location_id": self.stock_location_a.id,
                    "product_id": product.id,
                    "inventory_quantity": 0,
                }
            )
        )
        self.assertEqual(inventory_quant.company_id, self.company_a)
        inventory_quant.with_user(self.user_b).inventory_quantity = 10
        inventory_quant.with_user(self.user_b).action_apply_inventory()
        last_move_id = self.env["stock.move"].search([("is_inventory", "=", True)])[-1]
        self.assertEqual(inventory_quant.company_id, self.company_a)
        self.assertEqual(last_move_id.company_id, self.company_a)
        self.assertEqual(last_move_id.quantity, 10)
        self.assertEqual(last_move_id.location_id.company_id, self.company_a)

    def test_inventory_2(self):
        product = self.env["product.product"].create(
            {
                "name": "product limited to company b",
                "company_id": self.company_b.id,
                "is_storable": True,
            }
        )

        with self.assertRaises(UserError):
            self.env["stock.quant"].with_user(self.user_a).with_context(
                inventory_mode=True
            ).create(
                {
                    "location_id": self.stock_location_a.id,
                    "product_id": product.id,
                    "inventory_quantity": 10,
                }
            )

    def test_picking_1(self):
        picking_type_company_b = self.env["stock.picking.type"].search(
            [("company_id", "=", self.company_b.id)], limit=1
        )
        picking_form = Form(self.env["stock.picking"].with_user(self.user_a))
        picking_form.picking_type_id = picking_type_company_b
        picking = picking_form.save()
        self.assertEqual(picking.company_id, self.company_b)

    def test_location_1(self):
        with self.assertRaises(UserError):
            self.stock_location_b.location_id = self.stock_location_a

    def test_lot_2(self):
        product = self.env["product.product"].create(
            {
                "is_storable": True,
                "tracking": "serial",
                "name": "product",
                "company_id": self.company_a.id,
            }
        )
        picking = (
            self.env["stock.picking"]
            .with_user(self.user_a)
            .create(
                {
                    "picking_type_id": self.warehouse_a.in_type_id.id,
                    "location_id": self.env.ref("stock.stock_location_suppliers").id,
                    "location_dest_id": self.stock_location_a.id,
                    "state": "draft",
                }
            )
        )
        self.assertEqual(picking.company_id, self.company_a)
        move1 = self.env["stock.move"].create(
            {
                "picking_type_id": picking.picking_type_id.id,
                "location_id": picking.location_id.id,
                "location_dest_id": picking.location_dest_id.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
                "product_uom_qty": 1.0,
                "picking_id": picking.id,
                "company_id": picking.company_id.id,
            }
        )
        picking.with_user(self.user_b).action_confirm()
        self.assertEqual(picking.state, "assigned")
        move1.with_user(self.user_b).move_line_ids[0].quantity = 1
        move1.with_user(self.user_b).move_line_ids[0].lot_name = "receipt_serial"
        self.assertEqual(move1.move_line_ids[0].company_id, self.company_a)
        picking.with_user(self.user_b).move_ids.picked = True
        picking.with_user(self.user_b).button_validate()
        self.assertEqual(picking.state, "done")
        created_serial = self.env["stock.lot"].search([("name", "=", "receipt_serial")])
        self.assertEqual(created_serial.company_id, self.company_a)

    def test_lot_3(self):
        product = self.env["product.product"].create(
            {
                "type": "consu",
                "is_storable": True,
                "tracking": "serial",
                "name": "Cross-Company Product",
            }
        )
        lot = self.env["stock.lot"].create(
            {
                "name": "unique",
                "product_id": product.id,
                "company_id": self.company_a.id,
            }
        )
        self.assertTrue(lot)
        with self.assertRaises(ValidationError):
            self.env["stock.lot"].with_user(self.user_b).with_context(
                allowed_company_ids=self.company_b.ids
            ).create(
                {
                    "name": "unique",
                    "product_id": product.id,
                    "company_id": False,
                }
            )
        lot_b = (
            self.env["stock.lot"]
            .with_user(self.user_b)
            .create(
                {
                    "name": "unique",
                    "product_id": product.id,
                    "company_id": self.company_b.id,
                }
            )
        )
        self.assertTrue(lot_b)

    def test_orderpoint_1(self):
        self.user_a.group_ids += self.env.ref("stock.group_stock_multi_locations")
        product = self.env["product.product"].create(
            {
                "is_storable": True,
                "name": "shared product",
            }
        )
        orderpoint = Form(self.env["stock.warehouse.orderpoint"].with_user(self.user_a))
        orderpoint.company_id = self.company_b
        orderpoint.warehouse_id = self.warehouse_b
        orderpoint.location_id = self.stock_location_a
        orderpoint.product_id = product
        with self.assertRaises(UserError):
            orderpoint.save()
        orderpoint.location_id = self.stock_location_b
        orderpoint = orderpoint.save()
        self.assertEqual(orderpoint.company_id, self.company_b)

    def test_orderpoint_2(self):
        self.user_a.group_ids += self.env.ref("stock.group_stock_multi_locations")
        product = self.env["product.product"].create(
            {
                "is_storable": True,
                "name": "shared product",
            }
        )
        orderpoint = Form(self.env["stock.warehouse.orderpoint"].with_user(self.user_a))
        orderpoint.company_id = self.company_a
        orderpoint.warehouse_id = self.warehouse_a
        orderpoint.location_id = self.stock_location_a
        orderpoint.product_id = product
        orderpoint = orderpoint.save()
        self.assertEqual(orderpoint.company_id, self.company_a)
        with self.assertRaises(UserError):
            orderpoint.company_id = self.company_b.id

    def test_orderpoint_3(self):
        warehouse_a1 = self.warehouse_a
        warehouse_a2 = (
            self.env["stock.warehouse"]
            .with_user(self.user_a)
            .sudo()
            .create({"name": "foo", "code": "foo"})
        )
        product = self.env["product.product"].create(
            {
                "is_storable": True,
                "name": "shared product",
            }
        )
        orderpoint = (
            self.env["stock.warehouse.orderpoint"]
            .with_user(self.user_a)
            .create(
                {
                    "product_id": product.id,
                }
            )
        )
        self.assertEqual(orderpoint.warehouse_id, warehouse_a1)
        self.assertEqual(orderpoint.location_id, warehouse_a1.lot_stock_id)

        orderpoint.warehouse_id = warehouse_a2
        self.assertEqual(orderpoint.location_id, warehouse_a2.lot_stock_id)

        orderpoint.location_id = warehouse_a1.lot_stock_id
        self.assertEqual(orderpoint.warehouse_id, warehouse_a1)

        orderpoint.location_id = warehouse_a2.lot_stock_id
        self.assertEqual(orderpoint.warehouse_id, warehouse_a2)

    def test_product_1(self):
        self.user_a.group_ids += self.env.ref("product.group_product_manager")
        product_form = Form(self.env["product.template"].with_user(self.user_a))
        product_form.name = "Paramite Pie"
        product_form.responsible_id = self.user_b
        product = product_form.save()

        self.assertEqual(product.company_id.id, False)
        self.assertEqual(product.responsible_id.id, self.user_b.id)

        self.user_b.company_ids = [(6, 0, [self.company_b.id])]
        product_form = Form(self.env["product.template"].with_user(self.user_a))
        product_form.name = "Meech Munchy"
        product_form.company_id = self.company_a
        product_form.responsible_id = self.user_b

        with self.assertRaises(UserError):
            product = product_form.save()

        self.user_b.company_ids = [(6, 0, [self.company_a.id, self.company_b.id])]
        product_form = Form(self.env["product.template"].with_user(self.user_a))
        product_form.name = "Scrab Cake"
        product_form.company_id = self.company_a
        product_form.responsible_id = self.user_b
        product = product_form.save()

        self.assertEqual(product.company_id.id, self.company_a.id)
        self.assertEqual(product.responsible_id.id, self.user_b.id)

    def test_warehouse_1(self):
        with self.assertRaises(UserError):
            self.warehouse_a.company_id = self.company_b.id
        with self.assertRaises(UserError):
            self.warehouse_a.view_location_id = self.warehouse_b.view_location_id
        with self.assertRaises(UserError):
            self.warehouse_a.pick_type_id = self.warehouse_b.pick_type_id

    def test_move_1(self):
        product = self.env["product.product"].create(
            {"name": "p1", "is_storable": True}
        )
        picking_type_b = self.env["stock.picking.type"].search(
            [
                ("company_id", "=", self.company_b.id),
            ],
            limit=1,
        )
        move = self.env["stock.move"].create(
            {
                "company_id": self.company_a.id,
                "picking_type_id": picking_type_b.id,
                "location_id": self.stock_location_a.id,
                "location_dest_id": self.stock_location_a.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
            }
        )
        with self.assertRaises(UserError):
            move._action_confirm()

    def test_move_2(self):
        product = self.env["product.product"].create(
            {"name": "p1", "is_storable": True}
        )
        picking_type_b = self.env["stock.picking.type"].search(
            [
                ("company_id", "=", self.company_b.id),
            ],
            limit=1,
        )
        move = self.env["stock.move"].create(
            {
                "company_id": self.company_a.id,
                "picking_type_id": picking_type_b.id,
                "location_id": self.stock_location_a.id,
                "location_dest_id": self.stock_location_b.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
            }
        )
        with self.assertRaises(UserError):
            move._action_confirm()

    def test_move_3(self):
        product = self.env["product.product"].create(
            {
                "name": "p1",
                "is_storable": True,
                "company_id": self.company_b.id,
            }
        )
        picking_type_b = self.env["stock.picking.type"].search(
            [
                ("company_id", "=", self.company_b.id),
            ],
            limit=1,
        )
        move = self.env["stock.move"].create(
            {
                "company_id": self.company_a.id,
                "picking_type_id": picking_type_b.id,
                "location_id": self.stock_location_a.id,
                "location_dest_id": self.stock_location_a.id,
                "product_id": product.id,
                "product_uom_id": product.uom_id.id,
            }
        )
        with self.assertRaises(UserError):
            move._action_confirm()

    def test_intercom_lot_push(self):
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        intercom_location = self.env.ref("stock.stock_location_inter_company")
        intercom_location.write({"active": True})

        self.user_a.company_ids = [(6, 0, [self.company_a.id])]
        product_lot = self.env["product.product"].create(
            {
                "is_storable": True,
                "tracking": "lot",
                "name": "product lot",
            }
        )

        picking_type_to_transit = self.env["stock.picking.type"].create(
            {
                "name": "To Transit",
                "sequence_code": "TRANSIT",
                "code": "outgoing",
                "company_id": self.company_a.id,
                "warehouse_id": False,
                "default_location_src_id": self.stock_location_a.id,
                "default_location_dest_id": intercom_location.id,
                "sequence_id": self.env["ir.sequence"]
                .create(
                    {
                        "code": "transit",
                        "name": "transit sequence",
                        "company_id": self.company_a.id,
                    }
                )
                .id,
            }
        )

        route = self.env["stock.route"].create(
            {
                "name": "Push",
                "company_id": False,
                "rule_ids": [
                    (
                        0,
                        False,
                        {
                            "name": "create a move to company b",
                            "company_id": self.company_b.id,
                            "location_src_id": intercom_location.id,
                            "location_dest_id": self.stock_location_b.id,
                            "action": "push",
                            "auto": "manual",
                            "picking_type_id": self.warehouse_b.in_type_id.id,
                        },
                    )
                ],
            }
        )

        move_from_supplier = (
            self.env["stock.move"]
            .with_user(self.user_a)
            .create(
                {
                    "company_id": self.company_a.id,
                    "location_id": supplier_location.id,
                    "location_dest_id": self.stock_location_a.id,
                    "product_id": product_lot.id,
                    "product_uom_id": product_lot.uom_id.id,
                    "product_uom_qty": 0.1,
                    "picking_type_id": self.warehouse_a.in_type_id.id,
                }
            )
        )
        move_from_supplier._action_confirm()
        move_line_1 = move_from_supplier.move_line_ids[0]
        move_line_1.lot_name = "lot 1"
        move_line_1.quantity = 0.1
        move_from_supplier.picked = True
        move_from_supplier._action_done()
        lot = move_line_1.lot_id

        move_to_transit = self.env["stock.move"].create(
            {
                "company_id": self.company_a.id,
                "location_id": self.stock_location_a.id,
                "location_dest_id": intercom_location.id,
                "product_id": product_lot.id,
                "product_uom_id": product_lot.uom_id.id,
                "product_uom_qty": 0.1,
                "picking_type_id": picking_type_to_transit.id,
                "route_ids": [(4, route.id)],
            }
        )
        move_to_transit.with_user(self.user_a)._action_confirm()
        move_to_transit.with_user(self.user_a)._action_assign()
        move_line_2 = move_to_transit.move_line_ids[0]
        self.assertTrue(move_line_2.lot_id, move_line_1.lot_id)
        move_line_2.quantity = 0.1
        move_to_transit.picked = True
        move_to_transit.with_user(self.user_a)._action_done()

        move_push = self.env["stock.move"].search(
            [
                ("location_id", "=", intercom_location.id),
                ("product_id", "=", product_lot.id),
            ]
        )
        self.assertTrue(move_push, "No move created from push rules")
        self.assertEqual(move_push.state, "assigned")
        self.assertTrue(move_push.move_line_ids, "No move line created for the move")
        self.assertTrue(
            move_push in move_to_transit.move_dest_ids, "Moves are not chained"
        )
        self.assertEqual(
            move_push.move_line_ids.lot_id,
            move_line_2.lot_id,
            "Should be reserved from transit location",
        )
        picking_receipt = move_push.picking_id
        move_line_3 = move_push.move_line_ids[0]
        picking_receipt.move_ids.picked = True
        picking_receipt.button_validate()
        self.assertEqual(move_line_3.lot_id, lot)
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product_lot, intercom_location, lot
            ),
            0,
        )
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product_lot, self.stock_location_b, lot
            ),
            0.1,
        )

    def test_intercom_lot_pull(self):
        customer_location = self.env.ref("stock.stock_location_customers")
        supplier_location = self.env.ref("stock.stock_location_suppliers")
        intercom_location = self.env.ref("stock.stock_location_inter_company")
        intercom_location.write({"active": True})
        partner = self.env["res.partner"].create({"name": "Acme Corporation"})
        self.warehouse_a.resupply_wh_ids = [(6, 0, [self.warehouse_b.id])]
        resupply_route = self.env["stock.route"].search(
            [
                ("supplier_wh_id", "=", self.warehouse_b.id),
                ("supplied_wh_id", "=", self.warehouse_a.id),
            ]
        )
        self.assertTrue(resupply_route, "Resupply route not found")

        product_lot = self.env["product.product"].create(
            {
                "is_storable": True,
                "tracking": "lot",
                "name": "product lot",
                "route_ids": [
                    (4, resupply_route.id),
                    (4, self.env.ref("stock.route_warehouse0_mto").id),
                ],
            }
        )

        move_sup_to_whb = self.env["stock.move"].create(
            {
                "company_id": self.company_b.id,
                "location_id": supplier_location.id,
                "location_dest_id": self.warehouse_b.lot_stock_id.id,
                "product_id": product_lot.id,
                "product_uom_id": product_lot.uom_id.id,
                "product_uom_qty": 1.0,
                "picking_type_id": self.warehouse_b.in_type_id.id,
            }
        )
        move_sup_to_whb._action_confirm()
        move_line_1 = move_sup_to_whb.move_line_ids[0]
        move_line_1.lot_name = "lot a"
        move_line_1.quantity = 1.0
        move_sup_to_whb.picked = True
        move_sup_to_whb._action_done()
        lot_a = move_line_1.lot_id

        picking_out = self.env["stock.picking"].create(
            {
                "company_id": self.company_a.id,
                "partner_id": partner.id,
                "picking_type_id": self.warehouse_a.out_type_id.id,
                "location_id": self.stock_location_a.id,
                "location_dest_id": customer_location.id,
                "state": "draft",
            }
        )
        move_wha_to_cus = self.env["stock.move"].create(
            {
                "product_id": product_lot.id,
                "product_uom_qty": 1,
                "product_uom_id": product_lot.uom_id.id,
                "picking_id": picking_out.id,
                "location_id": self.stock_location_a.id,
                "location_dest_id": customer_location.id,
                "warehouse_id": self.warehouse_a.id,
                "procure_method": "make_to_order",
                "company_id": self.company_a.id,
            }
        )
        picking_out.action_confirm()

        move_whb_to_transit = self.env["stock.move"].search(
            [
                ("location_id", "=", self.stock_location_b.id),
                ("product_id", "=", product_lot.id),
            ]
        )
        move_transit_to_wha = self.env["stock.move"].search(
            [
                ("location_id", "=", intercom_location.id),
                ("product_id", "=", product_lot.id),
            ]
        )
        self.assertTrue(move_whb_to_transit, "No move created by pull rule")
        self.assertTrue(move_transit_to_wha, "No move created by pull rule")
        self.assertTrue(
            move_wha_to_cus in move_transit_to_wha.move_dest_ids,
            "Moves are not chained",
        )
        self.assertTrue(
            move_transit_to_wha in move_whb_to_transit.move_dest_ids,
            "Moves are not chained",
        )
        self.assertEqual(move_wha_to_cus.state, "waiting")
        self.assertEqual(move_transit_to_wha.state, "waiting")
        self.assertEqual(move_whb_to_transit.state, "assigned")

        (
            move_wha_to_cus + move_whb_to_transit + move_transit_to_wha
        ).picking_id.action_assign()
        self.assertEqual(move_wha_to_cus.state, "waiting")
        self.assertEqual(move_transit_to_wha.state, "waiting")
        self.assertEqual(move_whb_to_transit.state, "assigned")
        move_whb_to_transit.picking_id.button_validate()
        intercom_quant = self.env["stock.quant"].search(
            [
                ("lot_id", "=", lot_a.id),
                ("product_id", "=", product_lot.id),
                ("location_id", "=", intercom_location.id),
            ]
        )
        self.assertRecordValues(
            intercom_quant, [{"quantity": 1, "reserved_quantity": 1}]
        )

        move_line_2 = move_transit_to_wha.move_line_ids[0]
        self.assertEqual(move_line_2.lot_id, lot_a)
        move_line_2.quantity = 1.0
        move_transit_to_wha.picked = True
        move_transit_to_wha._action_done()

        move_wha_to_cus._action_assign()
        self.assertEqual(move_wha_to_cus.state, "assigned")
        move_wha_to_cus.picking_id.button_validate()
        self.assertEqual(
            self.env["stock.quant"]._get_available_quantity(
                product_lot, customer_location, lot_a
            ),
            1.0,
        )

        self.assertEqual(lot_a.name, "lot a")

    def test_intercom_pull_and_cancel(self):
        intercom_location = self.env.ref("stock.stock_location_inter_company")
        intercom_location.write({"active": True})
        self.warehouse_a.resupply_wh_ids = [(6, 0, [self.warehouse_b.id])]
        self.warehouse_a.resupply_route_ids.rule_ids.propagate_cancel = True
        product = self.env["product.product"].create(
            {
                "name": "product",
                "is_storable": True,
                "route_ids": [(6, 0, self.warehouse_a.resupply_route_ids.ids)],
            }
        )

        self.env["stock.quant"]._update_available_quantity(
            product, self.stock_location_a, -10
        )
        orderpoint = self.env["stock.warehouse.orderpoint"].create(
            {
                "name": "Test Orderpoint",
                "location_id": self.stock_location_a.id,
                "product_id": product.id,
                "company_id": self.company_a.id,
            }
        )

        orderpoint._procure_orderpoint_confirm()
        moves = self.env["stock.move"].search([("product_id", "=", product.id)])
        self.assertEqual(len(moves), 2)
        in_move = moves.filtered(lambda m: m.location_dest_id == self.stock_location_a)
        out_move = moves.filtered(lambda m: m.location_id == self.stock_location_b)
        in_move._action_cancel()
        self.assertEqual(in_move.state, "cancel")
        self.assertEqual(out_move.state, "confirmed")
        out_move._action_cancel()
        self.assertEqual(out_move.state, "cancel")

        self.env["ir.config_parameter"].sudo().set_param(
            "stock.cancel_moves_origin", True
        )
        orderpoint._procure_orderpoint_confirm()
        moves = self.env["stock.move"].search(
            [("product_id", "=", product.id), ("state", "!=", "cancel")]
        )
        self.assertEqual(len(moves), 2)
        in_move = moves.filtered(lambda m: m.location_dest_id == self.stock_location_a)
        out_move = moves.filtered(lambda m: m.location_id == self.stock_location_b)
        in_move._action_cancel()
        self.assertEqual(in_move.state, "cancel")
        self.assertEqual(out_move.state, "cancel")

    def test_route_rules_company_consistency(self):
        route = self.env["stock.route"].create(
            {
                "name": "Test Route",
                "company_id": self.company_a.id,
                "rule_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Buy",
                            "action": "pull_push",
                            "company_id": self.company_a.id,
                            "location_dest_id": self.stock_location_a.id,
                            "picking_type_id": self.warehouse_a.in_type_id.id,
                        },
                    )
                ],
            }
        )

        with self.assertRaises(ValidationError):
            route.write({"company_id": self.company_b.id})

        with self.assertRaises(ValidationError):
            route.write(
                {
                    "rule_ids": [
                        (
                            0,
                            0,
                            {
                                "name": "Buy",
                                "action": "pull_push",
                                "company_id": self.company_b.id,
                                "location_dest_id": self.stock_location_b.id,
                                "picking_type_id": self.warehouse_b.in_type_id.id,
                            },
                        )
                    ]
                }
            )
