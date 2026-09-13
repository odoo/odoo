from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain

from ..tools import debug_log as dbg


class StockPutawayRule(models.Model):
    _name = "stock.putaway.rule"
    _order = "sequence,product_id"
    _description = "Putaway Rule"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda s: s.env.company.id,
        index=True,
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        default=lambda self: self._default_product_id(),
        index="btree_not_null",
        domain="[('product_tmpl_id', '=', context.get('active_id', False))] if context.get('active_model') == 'product.template' else [('type', '!=', 'service')]",
        ondelete="cascade",
        check_company=True,
    )
    category_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        default=lambda self: self._default_category_id(),
        index="btree_not_null",
        domain=[("filter_for_stock_putaway_rule", "=", True)],
        ondelete="cascade",
    )
    location_in_id = fields.Many2one(
        comodel_name="stock.location",
        string="When product arrives in",
        default=lambda self: self._default_location_in_id(),
        index=True,
        required=True,
        domain="[('child_ids', '!=', False)]",
        ondelete="cascade",
        check_company=True,
    )
    location_out_id = fields.Many2one(
        comodel_name="stock.location",
        string="Store to sublocation",
        required=True,
        domain="[('id', 'child_of', location_in_id)]",
        ondelete="cascade",
        check_company=True,
    )
    active = fields.Boolean(default=True)
    sequence = fields.Integer(
        string="Priority",
        help="Give to the more specialized category, a higher priority to have them in top of the list.",
    )
    package_type_ids = fields.Many2many(
        comodel_name="stock.package.type",
        check_company=True,
    )
    storage_category_id = fields.Many2one(
        comodel_name="stock.storage.category",
        compute="_compute_storage_category_id",
        store=True,
        readonly=False,
        ondelete="cascade",
        check_company=True,
    )
    sublocation = fields.Selection(
        selection=[
            ("no", "No"),
            ("last_used", "Last Used"),
            ("closest_location", "Closest Location"),
        ],
        default="no",
    )

    def write(self, vals):
        if "company_id" in vals:
            for rule in self:
                if rule.company_id.id != vals["company_id"]:
                    raise UserError(
                        _(
                            "Changing the company of this record is forbidden at this point, you should rather archive it and create a new one."
                        ),
                    )
        return super().write(vals)

    @api.depends("sublocation")
    def _compute_storage_category_id(self):
        for rule in self:
            if rule.sublocation != "closest_location":
                rule.storage_category_id = False

    @api.onchange("sublocation", "location_out_id", "storage_category_id")
    def _onchange_sublocation(self):
        if self.sublocation == "closest_location":
            child_location_ids = self.env["stock.location"].search(
                [
                    ("id", "child_of", self.location_out_id.id),
                    ("storage_category_id", "=", self.storage_category_id.id),
                ]
            )
            if not child_location_ids:
                return {
                    "warning": {
                        "title": _("Warning"),
                        "message": _(
                            "Selected storage category does not exist in the 'store to' location or any of its sublocations"
                        ),
                    },
                }
        return None

    @api.onchange("location_in_id")
    def _onchange_location_in_id(self):
        loc_in, loc_out = self.location_in_id, self.location_out_id
        if not loc_out or (loc_in and not loc_out._is_child_of(loc_in)):
            self.location_out_id = self.location_in_id

    def _default_category_id(self):
        if self.env.context.get("active_model") == "product.category":
            return self.env.context.get("active_id")
        return None

    def _default_location_in_id(self):
        if self.env.context.get("active_model") == "stock.location":
            return self.env.context.get("active_id")
        if not self.env.user.has_group("stock.group_stock_multi_warehouses"):
            wh = self.env["stock.warehouse"].search(
                self.env["stock.warehouse"]._check_company_domain(self.env.company),
                limit=1,
            )
            input_loc, __ = wh._get_input_output_locations()
            return input_loc
        return None

    def _default_product_id(self):
        if self.env.context.get(
            "active_model"
        ) == "product.template" and self.env.context.get("active_id"):
            product_template = self.env["product.template"].browse(
                self.env.context.get("active_id")
            )
            product_template = product_template.exists()
            if product_template.product_variant_count == 1:
                return product_template.product_variant_id
        elif self.env.context.get("active_model") == "product.product":
            return self.env.context.get("active_id")
        return None

    def _get_domain_last_used_search(self, product):
        self.check_singleton()
        domain = Domain(
            [
                ("state", "=", "done"),
                ("location_dest_id", "child_of", self.location_out_id.id),
                ("product_id", "=", product.id),
            ],
        )
        if self.package_type_ids:
            domain &= Domain(
                "result_package_id.package_type_id",
                "in",
                self.package_type_ids.ids,
            )
        return domain

    def _get_last_used_location(self, product):
        self.check_singleton()
        location = (
            self.env["stock.move.line"]
            .search(
                domain=self._get_domain_last_used_search(product),
                limit=1,
                order="date desc",
            )
            .location_dest_id
        )
        dbg.logic.debug(
            "[putaway_rule:%s] last used location for product %s: %s",
            self.id,
            product.id,
            location.id,
        )
        return location

    @dbg.timed
    def _get_putaway_location(
        self,
        product,
        quantity=0,
        package=None,
        packaging=None,
        qty_by_location=None,
    ):
        if qty_by_location is None:
            qty_by_location = defaultdict(float)
        package_type = self.env["stock.package.type"]
        if package:
            package_type = package.package_type_id
        elif packaging:
            package_type = packaging.package_type_id

        checked_locations = set()
        for putaway_rule in self:
            location_out = putaway_rule.location_out_id
            if putaway_rule.sublocation == "last_used":
                location_dest_id = putaway_rule._get_last_used_location(product)
                location_out = location_dest_id or location_out

            if not putaway_rule.storage_category_id:
                if location_out in checked_locations:
                    continue
                if location_out._can_be_used(
                    product, quantity, package, qty_by_location[location_out.id]
                ):
                    dbg.logic.debug(
                        "[putaway_rule:%s] direct location %s",
                        putaway_rule.id,
                        location_out.id,
                    )
                    return location_out
                checked_locations.add(location_out)
                continue
            child_locations = location_out.child_internal_location_ids.filtered(
                lambda loc, putaway_rule=putaway_rule: (
                    loc.storage_category_id == putaway_rule.storage_category_id
                )
            )
            dbg.logic.debug(
                "[putaway_rule:%s] storage category %s: %d candidate locations under %s",
                putaway_rule.id,
                putaway_rule.storage_category_id.id,
                len(child_locations),
                location_out.id,
            )

            capacity = child_locations._get_putaway_capacity(product, package)

            for location in child_locations:
                if location in checked_locations:
                    continue
                if package_type:
                    if location.quant_ids.filtered(
                        lambda q: (
                            q.package_id
                            and q.package_id.package_type_id == package_type
                        )
                    ):
                        if location._can_be_used(
                            product,
                            quantity,
                            package=package,
                            location_qty=qty_by_location[location.id],
                            capacity=capacity,
                        ):
                            return location
                        else:
                            checked_locations.add(location)
                elif product.uom_id.compare(qty_by_location[location.id], 0) > 0:
                    if location._can_be_used(
                        product,
                        quantity,
                        location_qty=qty_by_location[location.id],
                        capacity=capacity,
                    ):
                        return location
                    else:
                        checked_locations.add(location)

            for location in child_locations:
                if location in checked_locations:
                    continue
                if location._can_be_used(
                    product,
                    quantity,
                    package,
                    qty_by_location[location.id],
                    capacity=capacity,
                ):
                    dbg.logic.debug(
                        "[putaway_rule:%s] first free location %s",
                        putaway_rule.id,
                        location.id,
                    )
                    return location
                checked_locations.add(location)

        dbg.logic.debug(
            "_get_putaway_location: no rule of %s fits product %s (%d locations checked)",
            dbg.rec(self),
            product.id,
            len(checked_locations),
        )
        return None
