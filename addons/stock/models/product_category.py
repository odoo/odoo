from odoo import api, fields, models
from odoo.fields import Domain

from ..tools import debug_log as dbg


class ProductCategory(models.Model):
    _inherit = "product.category"

    removal_strategy_id = fields.Many2one(
        comodel_name="product.removal",
        string="Force Removal Strategy",
        tracking=True,
        help="Set a specific removal strategy that will be used regardless of the source location for this product category.\n\n"
        "FIFO: products/lots that were stocked first will be moved out first.\n"
        "LIFO: products/lots that were stocked last will be moved out first.\n"
        "Closest location: products/lots closest to the target location will be moved out first.\n"
        "FEFO: products/lots with the closest removal date will be moved out first "
        '(the availability of this method depends on the "Expiration Dates" setting).\n'
        "Least Packages: FIFO but with the least number of packages possible when there are several packages containing the same product.",
    )
    route_ids = fields.Many2many(
        comodel_name="stock.route",
        relation="stock_route_categ",
        column1="categ_id",
        column2="route_id",
        string="Routes",
        domain=[("product_categ_selectable", "=", True)],
    )
    parent_route_ids = fields.Many2many(
        comodel_name="stock.route",
        string="Parent Routes",
        compute="_compute_parent_route_ids",
    )
    total_route_ids = fields.Many2many(
        comodel_name="stock.route",
        string="Total routes",
        compute="_compute_total_route_ids",
        search="_search_total_route_ids",
        readonly=True,
    )
    packaging_reserve_method = fields.Selection(
        selection=[
            ("full", "Reserve Only Full Packagings"),
            ("partial", "Reserve Partial Packagings"),
        ],
        string="Reserve Packagings",
        default="partial",
        help="Reserve Only Full Packagings: will not reserve partial packagings. If customer orders 2 pallets of 1000 units each and you only have 1600 in stock, then only 1000 will be reserved\n"
        "Reserve Partial Packagings: allow reserving partial packagings. If customer orders 2 pallets of 1000 units each and you only have 1600 in stock, then 1600 will be reserved",
    )
    putaway_rule_ids = fields.One2many(
        comodel_name="stock.putaway.rule",
        inverse_name="category_id",
        string="Putaway Rules",
    )
    filter_for_stock_putaway_rule = fields.Boolean(
        string="stock.putaway.rule",
        search="_search_filter_for_stock_putaway_rule",
        store=False,
    )

    @dbg.timed
    @api.depends("parent_id", "parent_id.total_route_ids", "route_ids")
    def _compute_parent_route_ids(self):
        # The ancestry is walked over `route_ids`, a plain stored field, and
        # NOT read off `parent_id.total_route_ids`. Reading the parent's total
        # here is correct one record at a time and wrong for a batch: computing
        # the whole recordset at once reaches the parent's `total_route_ids`
        # while it is still being computed, and the in-progress value is empty,
        # so every descendant silently loses its ancestors' routes. Measured:
        # a three-deep chain reads [[sel], [sel], [sel]] single and
        # [[sel], [], []] batched. `total_route_ids` feeds route resolution in
        # stock_rule_selection, stock_orderpoint, sale_stock and
        # stock_dropshipping, and `mapped()` is the normal way they read it.
        #
        # `parent_id.total_route_ids` stays in the depends: a dependency drives
        # invalidation, not the value, so it propagates an edit one level down
        # without the body ever reading a field mid-compute.
        for category in self:
            ancestor = category
            routes = self.env["stock.route"]
            while ancestor.parent_id:
                ancestor = ancestor.parent_id
                routes |= ancestor.route_ids
            category.parent_route_ids = routes - category.route_ids

    @api.depends("route_ids", "parent_route_ids")
    def _compute_total_route_ids(self):
        for category in self:
            category.total_route_ids = category.route_ids | category.parent_route_ids

    def _search_total_route_ids(self, operator, value):
        # `filtered_domain` on this very leaf -- which is what this used to do
        # -- routes straight back here through the field's own `search=`, so
        # any search on `total_route_ids` raised `Domain nesting too deep to
        # optimize`. It is reachable: `product.template.route_from_categ_ids`
        # is `related="categ_id.total_route_ids"` and sits on the product form,
        # so a custom filter on it reaches this method. The leaf is therefore
        # evaluated by reading ids, never by re-entering the domain machinery.
        if operator not in ("in", "not in"):
            return NotImplemented
        wanted = {value} if isinstance(value, int) else set(value or ())
        if not all(isinstance(route_id, int) for route_id in wanted):
            return NotImplemented

        matched = []
        if wanted:
            # The relation table over-approximates on purpose: `route_ids`
            # carries `domain=[("product_categ_selectable", "=", True)]`, and a
            # relational field's domain is applied on READ, so a link to a
            # non-selectable route is in the table and absent from the field.
            # The table bounds the candidates -- only a category linking a
            # wanted route, or a descendant of one, can carry it in
            # `total_route_ids` -- and the read below decides. That is two
            # indexed queries where this used to scan every category.
            categories = self.with_context(active_test=False)
            owners = categories.search([("route_ids", "in", list(wanted))])
            if owners:
                candidates = categories.search([("id", "child_of", owners.ids)])
                matched = [
                    category.id
                    for category in candidates
                    if wanted & set(category.total_route_ids.ids)
                ]
                dbg.performance.debug(
                    "_search_total_route_ids(%s): %d owners -> %d candidates, %d match",
                    operator,
                    len(owners),
                    len(candidates),
                    len(matched),
                )
        return [("id", "in" if operator == "in" else "not in", matched)]

    def _search_filter_for_stock_putaway_rule(self, operator, value):
        if operator != "in":
            return NotImplemented

        domain = Domain.TRUE
        active_model = self.env.context.get("active_model")
        if active_model in (
            "product.template",
            "product.product",
        ) and self.env.context.get("active_id"):
            product = self.env[active_model].browse(self.env.context.get("active_id"))
            product = product.exists()
            if product:
                domain = Domain("id", "=", product.categ_id.id)
        return domain
