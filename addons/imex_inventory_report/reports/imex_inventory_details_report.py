
from odoo import api, fields, models, tools


class ImexInventoryDetailsReport(models.Model):
    _name = "imex.inventory.details.report"
    _description = "Imex Inventory Details Report"
    _auto = False

    date = fields.Datetime(readonly=True)
    product_id = fields.Many2one(comodel_name="product.product", readonly=True)
    product_qty = fields.Float(readonly=True)
    product_uom = fields.Many2one(comodel_name="uom.uom", readonly=True)
    product_category = fields.Many2one(
        comodel_name="product.category", readonly=True)
    unit_cost = fields.Float(readonly=True)
    reference = fields.Char(readonly=True)
    partner_id = fields.Many2one(comodel_name="res.partner", readonly=True)
    origin = fields.Char(readonly=True)
    location_id = fields.Many2one(comodel_name="stock.location", readonly=True)
    location_dest_id = fields.Many2one(
        comodel_name="stock.location", readonly=True)
    initial = fields.Float(readonly=True)
    initial_amount = fields.Float(readonly=True)
    product_in = fields.Float(readonly=True)
    product_out = fields.Float(readonly=True)
    picking_id = fields.Many2one(comodel_name="stock.picking", readonly=True)

    def name_get(self):
        result = []
        for rec in self:
            name = rec.reference
            if rec.picking_id.origin:
                name = "{} ({})".format(name, rec.picking_id.origin)
            result.append((rec.id, name))
        return result

    def _get_locations(self, location_id, is_groupby_location):
        if (location_id):
            if is_groupby_location:
                locations = tuple(self.env["stock.location"].search(
                    [("id", "child_of", location_id.ids)]).ids)
            else:
                locations = tuple(location_id.ids)
        else:
            locations = tuple(self.env["stock.location"].search(
                [("usage", "=", "internal")]).ids)
            if not locations:
                locations = (-1,)
        return locations

    def init_results(self, filter_fields):
        date_from = filter_fields.date_from or "1900-01-01"
        date_to = filter_fields.date_to or fields.Date.context_today(self)
        is_groupby_location = filter_fields.is_groupby_location

        locations = self._get_locations(
            filter_fields.location_id, is_groupby_location)
        product_ids = tuple(filter_fields.product_ids.ids)

        query_ = """
            SELECT row_number() OVER () AS id,* FROM(
                SELECT 
                    (SUM(CASE WHEN move.location_dest_id IN %s
                        THEN move.product_qty ELSE 0 END)
                    -
                    SUM(CASE WHEN move.location_id IN %s
                        THEN move.product_qty ELSE 0 END)) AS initial,
                    (SUM(CASE WHEN move.location_dest_id IN %s
                        THEN move.product_qty*svl.unit_cost ELSE 0 END)
                    -
                    SUM(CASE WHEN move.location_id IN %s
                        THEN move.product_qty*svl.unit_cost ELSE 0 END)) AS initial_amount,
                    null AS date, 
                    null AS product_id, 
                    null AS product_qty, 
                    null AS product_uom, 
                    null AS product_category,
                    null AS unit_cost, 
                    null AS reference, 
                    null AS partner_id, 
                    null AS origin, 
                    null AS location_id, 
                    null AS location_dest_id,
                    null AS product_in, 
                    null AS product_out, 
                    null AS picking_id
                FROM stock_move move
                    LEFT JOIN stock_valuation_layer svl on move.id = svl.stock_move_id
                WHERE 
                    (move.location_id in %s or move.location_dest_id in %s)
                    and move.state = 'done'
                    and move.product_id in %s
                    and CAST(move.date AS date) < %s 
                UNION ALL
                SELECT
                    null as initial, null as initial_amount,
                    move.date, 
                    move.product_id, 
                    move.product_qty,
                    move.product_uom, 
                    template.categ_id as product_category,
                    svl.unit_cost,
                    move.reference, 
                    move.partner_id, 
                    move.origin,                
                    move.location_id, 
                    move.location_dest_id,
                    case when move.location_dest_id in %s
                        then move.product_qty end as product_in,
                    case when move.location_id in %s
                        then move.product_qty end as product_out,
                    move.picking_id
                FROM stock_move move
                    LEFT JOIN stock_valuation_layer svl on move.id = svl.stock_move_id
                    LEFT JOIN product_product product on move.product_id = product.id
                        LEFT JOIN product_template template on product.product_tmpl_id = template.id
                WHERE 
                    (move.location_id in %s or move.location_dest_id in %s)
                    and move.state = 'done'
                    and move.product_id in %s
                    and CAST(move.date AS date) >= %s 
                    and CAST(move.date AS date) <= %s) AS a          
            ORDER BY a.date, a.reference
            """
        params = (locations,
                  locations,
                  locations,
                  locations,
                  locations,
                  locations,
                  product_ids,
                  date_from,
                  locations,
                  locations,
                  locations,
                  locations,
                  product_ids,
                  date_from,
                  date_to)

        tools.drop_view_if_exists(self._cr, self._table)
        res = self._cr.execute(
            """CREATE VIEW {} as ({})""".format(self._table, query_), params)
        return res

    # def print_report(self):
    #     action = self.env.ref(
    #         "imex_inventory_report.action_imex_inventory_details_report_pdf")
    #     vals = action.sudo().read()[0]
    #     context = vals.get("context", {})
    #     if context:
    #         context = safe_eval(context)
    #     context["active_ids"] = self._context.get("active_ids")
    #     context["details"] = self.browse(self._context.get("active_ids"))
    #     vals["data"] = self._context.get("data")
    #     vals["context"] = context
    #     return vals

    def _get_html(self):
        result = {}
        rcontext = {}
        report = self.browse(self._context.get("active_ids"))
        data = self._context.get("data")
        if report:
            rcontext["details"] = report
            rcontext["data"] = data
            result["html"] = self.env['ir.qweb']._render(
                "imex_inventory_report.imex_inventory_details_report", rcontext)
        return result

    @api.model
    def get_html(self, given_context=None):
        return self.with_context(**(given_context or {}))._get_html()
