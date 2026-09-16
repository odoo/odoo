from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import TransactionMemo

from ..tools import debug_log as dbg

ROUTE_RULE_ACTIONS = TransactionMemo(
    "stock.route.rule_actions", invalidated_by=("stock.rule",)
)


class StockRoute(models.Model):
    _name = "stock.route"
    _description = "Inventory Routes"
    _order = "sequence"
    _check_company_auto = True

    name = fields.Char(
        string="Route",
        translate=True,
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If the active field is set to False, it will allow you to hide the route without removing it.",
    )
    sequence = fields.Integer(default=0)
    rule_ids = fields.One2many(
        comodel_name="stock.rule",
        inverse_name="route_id",
        string="Rules",
        copy=True,
    )
    product_selectable = fields.Boolean(
        string="Applicable on Product",
        default=True,
        help="When checked, the route will be selectable in the Inventory tab of the Product form.",
    )
    product_categ_selectable = fields.Boolean(
        string="Applicable on Product Category",
        help="When checked, the route will be selectable on the Product Category.",
    )
    warehouse_selectable = fields.Boolean(
        string="Applicable on Warehouse",
        help="When a warehouse is selected for this route, this route should be seen as the default route when products pass through this warehouse.",
    )
    package_type_selectable = fields.Boolean(
        string="Applicable on Package Type",
        help="When checked, the route will be selectable on package types",
    )
    supplied_wh_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Supplied Warehouse",
        index="btree_not_null",
    )
    supplier_wh_id = fields.Many2one(
        comodel_name="stock.warehouse",
        string="Supplying Warehouse",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        index=True,
        help="Leave this field empty if this route is shared between all companies",
    )
    product_ids = fields.Many2many(
        comodel_name="product.template",
        relation="stock_route_product",
        column1="route_id",
        column2="product_id",
        string="Products",
        copy=False,
        check_company=True,
    )
    categ_ids = fields.Many2many(
        comodel_name="product.category",
        relation="stock_route_categ",
        column1="route_id",
        column2="categ_id",
        string="Product Categories",
        copy=False,
    )
    warehouse_domain_ids = fields.One2many(
        comodel_name="stock.warehouse",
        compute="_compute_warehouse_domain_ids",
    )
    warehouse_ids = fields.Many2many(
        comodel_name="stock.warehouse",
        relation="stock_route_warehouse",
        column1="route_id",
        column2="warehouse_id",
        string="Warehouses",
        copy=False,
        domain="[('id', 'in', warehouse_domain_ids)]",
    )

    def _has_rule_with_action(self, action):
        memo = ROUTE_RULE_ACTIONS(self.env)
        missing = [route_id for route_id in self.ids if route_id not in memo]
        if missing:
            memo.update(dict.fromkeys(missing, frozenset()))
            for route, actions in (
                self.env["stock.rule"]
                .sudo()
                ._read_group(
                    [("route_id", "in", missing)], ["route_id"], ["action:array_agg"]
                )
            ):
                memo[route.id] = frozenset(actions)
        return any(action in memo[route_id] for route_id in self.ids)

    @api.constrains("company_id", "rule_ids")
    def _check_company_consistency(self):
        for route in self:
            if not route.company_id:
                continue

            for rule in route.rule_ids:
                if route.company_id.id != rule.company_id.id:
                    raise ValidationError(
                        _(
                            "Rule %(rule)s belongs to %(rule_company)s while the route belongs to %(route_company)s.",
                            rule=rule.display_name,
                            rule_company=rule.company_id.display_name,
                            route_company=route.company_id.display_name,
                        ),
                    )

    @dbg.timed
    def write(self, vals):
        dbg.lifecycle.debug(
            "stock.route.write on %s: keys=%s", dbg.rec(self), dbg.keys(vals)
        )
        if "active" in vals:
            all_rules = self.with_context(active_test=False).rule_ids.sudo()
            dbg.lifecycle.debug(
                "stock.route.write: active=%s cascades to rules %s",
                vals["active"],
                dbg.rec(all_rules),
            )
            if vals["active"]:
                all_rules.filtered(
                    lambda rule: rule.location_dest_id.active
                ).action_unarchive()
            else:
                all_rules.action_archive()
        res = super().write(vals)
        if vals.get("active"):
            for warehouse in self.sudo().supplier_wh_id:
                warehouse._update_resupply_rule_activity()
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for route, vals in zip(self, vals_list, strict=True):
                vals["name"] = _("%s (copy)", route.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    @api.depends("company_id")
    def _compute_warehouse_domain_ids(self):
        Warehouse = self.env["stock.warehouse"]
        per_company = {
            company.id: Warehouse.search([("company_id", "=", company.id)])
            for company in self.company_id
        }
        if not all(route.company_id for route in self):
            per_company[False] = Warehouse.search([])
        for route in self:
            route.warehouse_domain_ids = per_company[route.company_id.id]

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            self.warehouse_ids = self.warehouse_ids.filtered(
                lambda w: w.company_id == self.company_id
            )

    @api.onchange("warehouse_selectable")
    def _onchange_warehouse_selectable(self):
        if not self.warehouse_selectable:
            self.warehouse_ids = [(5, 0, 0)]

    def _is_valid_resupply_route_for_product(self, product):
        return False
