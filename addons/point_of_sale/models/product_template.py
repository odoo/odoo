from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import SQL, is_html_empty

from ..tools import debug_log as dbg


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "mixin.pos.load"]

    available_in_pos = fields.Boolean(
        string="Available in POS",
        default=False,
        help="Check if you want this product to appear in the Point of Sale.",
    )
    to_weight = fields.Boolean(
        string="To Weigh With Scale",
        help="Check if the product should be weighted using the hardware scale integration.",
    )
    pos_categ_ids = fields.Many2many(
        comodel_name="pos.category",
        string="Point of Sale Category",
        help="Category used in the Point of Sale.",
    )
    public_description = fields.Html(
        string="Product Description",
        translate=True,
    )
    pos_optional_product_ids = fields.Many2many(
        comodel_name="product.template",
        relation="pos_product_optional_rel",
        column1="src_id",
        column2="dest_id",
        string="POS Optional Products",
        help="Optional products are suggested when customers add items to their cart (e.g., adding a burger suggests cold drinks or fries).",
    )
    color = fields.Integer(
        string="Color Index",
        compute="_compute_color",
        store=True,
        readonly=False,
    )
    pos_sequence = fields.Integer(
        string="POS Sequence",
        copy=False,
        help="Determine the display order in the POS Terminal",
    )

    @api.constrains("available_in_pos")
    def _check_available_in_pos(self):
        withdrawn = self.filtered(lambda template: not template.available_in_pos)
        if not withdrawn:
            return
        combo_item = (
            self.env["product.combo.item"]
            .sudo()
            .search(
                [("product_id", "in", withdrawn.product_variant_ids.ids)],
                limit=1,
            )
        )
        if combo_item:
            raise ValidationError(
                _(
                    "You must first remove this product from the %s combo",
                    combo_item.combo_id.name,
                )
            )

    @api.constrains("pos_optional_product_ids")
    def _check_pos_optional_product_ids(self):
        for template in self:
            if template in template.pos_optional_product_ids:
                raise ValidationError(
                    _(
                        "%s cannot be suggested as an optional product for itself.",
                        template.display_name,
                    )
                )

    def _check_unused_in_pos(self):
        if self._is_blocked_by_open_pos_session():
            raise UserError(
                _(
                    "Hold up! Archiving products while POS sessions are active is like pulling a plate mid-meal.\n"
                    "Make sure to close all sessions first to avoid any issues.",
                )
            )

    def _check_is_special_product(self):
        special = self._filtered_pos_special_products()
        if special:
            raise UserError(
                _(
                    "You cannot archive or delete %s: it is set as a special product "
                    "in a Point of Sale configuration. Please change the configuration first.",
                    special[0].display_name,
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._update_public_description_vals(vals_list)
        self._update_pos_sequence_vals(vals_list)
        for vals in vals_list:
            self._update_available_in_pos_vals(vals)
        dbg.lifecycle.debug(
            "product.template.create: %d vals, %d available_in_pos",
            len(vals_list),
            sum(1 for vals in vals_list if vals.get("available_in_pos")),
        )
        return super().create(vals_list)

    def write(self, vals):
        self._update_public_description_vals([vals])
        self._update_available_in_pos_vals(vals)
        if "active" in vals and not vals["active"]:
            dbg.lifecycle.debug(
                "product.template archive: %s (pos checks)", dbg.rec(self)
            )
            self._check_unused_in_pos()
            self._check_is_special_product()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_open_session(self):
        if self._is_blocked_by_open_pos_session():
            raise UserError(
                _(
                    "To delete a product, make sure all point of sale sessions are closed.\n\n"
                    "Deleting a product available in a session would be like attempting to snatch a hamburger from a customer’s hand mid-bite; chaos will ensue as ketchup and mayo go flying everywhere!",
                )
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_special_product(self):
        self._check_is_special_product()

    @api.depends("pos_categ_ids")
    def _compute_color(self):
        for product in self:
            if product.pos_categ_ids:
                product.color = product.pos_categ_ids[0].color
            else:
                product.color = product.color or 0

    @api.onchange("sale_ok")
    def _onchange_sale_ok(self):
        if not self.sale_ok:
            self.available_in_pos = False

    @api.onchange("available_in_pos")
    def _onchange_available_in_pos(self):
        if self.available_in_pos and not self.sale_ok:
            self.sale_ok = True

    def set_pos_favorite(self, is_favorite):
        self.check_singleton()
        dbg.lifecycle.debug(
            "product.template %s favorite -> %s", dbg.rec(self), bool(is_favorite)
        )
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("Only Point of Sale users can change a POS favorite."))
        if not self.available_in_pos:
            raise AccessError(
                _(
                    "%s is not available in the Point of Sale, so it cannot be "
                    "marked as a favorite there.",
                    self.display_name,
                )
            )
        self.sudo().is_favorite = bool(is_favorite)
        return self.is_favorite

    def create_product_variant_from_pos(self, attribute_value_ids, config_id):
        self.check_singleton()
        config = self.env["pos.config"].browse(config_id)
        config.check_access("read")
        attribute_values = self.env["product.template.attribute.value"].browse(
            attribute_value_ids
        )
        product_variant = self._create_product_variant(attribute_values)
        dbg.lifecycle.debug(
            "product.template %s: variant %s from attribute values %s",
            dbg.rec(self),
            dbg.rec(product_variant),
            attribute_value_ids,
        )
        return {
            "product.product": self.env["product.product"]._load_pos_data_read(
                product_variant, config
            ),
        }

    @dbg.timed
    def get_product_info_pos(
        self, price, quantity, pos_config_id, product_variant_id=False
    ):
        self.check_singleton()
        config = self.env["pos.config"].browse(pos_config_id)
        config.check_access("read")
        product_variant = (
            self.env["product.product"].browse(product_variant_id)
            if product_variant_id
            else self.env["product.product"]
        )
        template_or_variant = product_variant or self.product_variant_id

        return {
            "all_prices": self._get_pos_price_info(
                price, quantity, config, product_variant or self
            ),
            "pricelists": self._get_pos_pricelist_info(
                config, template_or_variant, quantity
            ),
            "warehouses": self._get_pos_warehouse_info(config, template_or_variant),
            "suppliers": self._get_pos_supplier_info(quantity),
            "variants": self._get_pos_variant_info(),
            "optional_products": self.pos_optional_product_ids.read(
                ["id", "name", "list_price"]
            ),
        }

    def _get_pos_price_info(self, price, quantity, config, product):
        taxes = self._get_taxes_of_nearest_company(config.company_id)
        computed = taxes.sudo().compute_all(
            price, config.currency_id, quantity, product.sudo()
        )
        per_unit = quantity or 1

        grouped_taxes = {}
        for tax in computed["taxes"]:
            amount = tax["amount"] / per_unit if quantity else 0
            if tax["id"] in grouped_taxes:
                grouped_taxes[tax["id"]]["amount"] += amount
            else:
                grouped_taxes[tax["id"]] = {"name": tax["name"], "amount": amount}

        return {
            "price_without_tax": (
                computed["total_excluded"] / per_unit if quantity else 0
            ),
            "price_with_tax": computed["total_included"] / per_unit if quantity else 0,
            "tax_details": list(grouped_taxes.values()),
        }

    def _get_taxes_of_nearest_company(self, company):
        return self.taxes_id.browse(
            self._get_tax_ids_of_nearest_company(
                self.taxes_id.ids, self._get_taxes_by_company(self.taxes_id), company
            )
        )

    def _get_pos_pricelist_info(self, config, product, quantity):
        pricelists = (
            config.available_pricelist_ids
            if config.use_pricelist
            else config.pricelist_id
        )
        if not pricelists:
            return []
        price_by_pricelist_id = pricelists._price_get(product, quantity)
        return [
            {"name": pricelist.name, "price": price_by_pricelist_id[pricelist.id]}
            for pricelist in pricelists
        ]

    def _get_pos_warehouse_info(self, config, product):
        warehouses = self.env["stock.warehouse"].search(
            [("company_id", "=", config.company_id.id)]
        )
        pos_warehouse_id = config.picking_type_id.warehouse_id.id
        warehouse_info = []
        for warehouse in warehouses:
            in_warehouse = product.with_context(warehouse_id=warehouse.id)
            warehouse_info.append(
                {
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "available_quantity": in_warehouse.qty_available,
                    "qty_free": in_warehouse.qty_free,
                    "forecasted_quantity": in_warehouse.qty_available_virtual,
                    "uom": product.uom_name,
                }
            )
        if pos_warehouse_id:
            warehouse_info.sort(key=lambda info: info["id"] != pos_warehouse_id)
        return warehouse_info

    def _get_pos_supplier_info(self, quantity):
        today = fields.Date.today()
        supplier_info = {}
        for seller in self.seller_ids:
            if seller.partner_id.id in supplier_info:
                continue
            if (
                (seller.date_start and seller.date_start > today)
                or (seller.date_end and seller.date_end < today)
                or seller.min_qty > quantity
            ):
                continue
            supplier_info[seller.partner_id.id] = {
                "id": seller.id,
                "name": seller.partner_id.name,
                "delay": seller.delay,
                "price": seller.price,
            }
        return list(supplier_info.values())

    def _get_pos_variant_info(self):
        return [
            {
                "name": attribute_line.attribute_id.name,
                "values": [
                    {"name": attr_name, "search": f"{self.name} {attr_name}"}
                    for attr_name in attribute_line.value_ids.mapped("name")
                ],
            }
            for attribute_line in self.attribute_line_ids
        ]

    @api.model
    def _update_available_in_pos_vals(self, vals):
        if "sale_ok" in vals and not vals["sale_ok"]:
            vals["available_in_pos"] = False

    @api.model
    def _update_public_description_vals(self, vals_list):
        for vals in vals_list:
            description = vals.get("public_description")
            if description and is_html_empty(description):
                vals["public_description"] = ""

    @api.model
    def _update_pos_sequence_vals(self, vals_list):
        pending = [vals for vals in vals_list if not vals.get("pos_sequence")]
        if not pending:
            return
        self.flush_model(["pos_sequence"])
        rows = self.env.execute_query(
            SQL("SELECT MAX(pos_sequence) FROM %s", SQL.identifier(self._table))
        )
        next_sequence = (rows[0][0] or 0) + 1
        dbg.logic.debug(
            "product.template pos_sequence: %d pending from %s",
            len(pending),
            next_sequence,
        )
        for offset, vals in enumerate(pending):
            vals["pos_sequence"] = next_sequence + offset

    def _filtered_pos_special_products(self):
        config = self.env["pos.config"].sudo()
        special = (
            config.search([])._get_special_products() | config._get_special_products()
        )
        return self & special.product_tmpl_id

    def _is_blocked_by_open_pos_session(self):
        return bool(
            any(self.mapped("available_in_pos"))
            and self.env["pos.session"]
            .sudo()
            .search_count([("state", "!=", "closed")], limit=1)
        )
