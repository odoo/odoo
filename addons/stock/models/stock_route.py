from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockRoute(models.Model):
    _name = "stock.route"
    _description = "Inventory Routes"
    _order = "sequence"
    _check_company_auto = True

    name = fields.Char(
        string="Route",
        required=True,
        translate=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        help="If the active field is set to False, it will allow you to hide the route without removing it.",
    )
    sequence = fields.Integer(string="Sequence", default=0)
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
    supplier_wh_id = fields.Many2one("stock.warehouse", "Supplying Warehouse")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
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
        compute="_compute_warehouses",
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

    @api.constrains("company_id")
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

    def write(self, vals):
        if "active" in vals:
            rules = (
                self.with_context(active_test=False)
                .rule_ids.sudo()
                .filtered(lambda rule: rule.location_dest_id.active)
            )
            if vals["active"]:
                rules.action_unarchive()
            else:
                rules.action_archive()
        return super().write(vals)

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for route, vals in zip(self, vals_list):
                vals["name"] = _("%s (copy)", route.name)
        return vals_list

    @api.depends("company_id")
    def _compute_warehouses(self):
        for loc in self:
            domain = [("company_id", "=", loc.company_id.id)] if loc.company_id else []
            loc.warehouse_domain_ids = self.env["stock.warehouse"].search(domain)

    @api.onchange("company_id")
    def _onchange_company(self):
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
