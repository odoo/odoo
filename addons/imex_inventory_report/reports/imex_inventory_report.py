
from odoo import api, fields, models, tools
from odoo.tools.safe_eval import safe_eval


class ImexInventoryReport(models.Model):
    _name = "imex.inventory.report"
    _description = "Imex Inventory Report"
    _auto = False

    product_id = fields.Many2one(comodel_name="product.product", readonly=True)
    product_uom = fields.Many2one(comodel_name="uom.uom", readonly=True)
    product_category = fields.Many2one(
        comodel_name="product.category", readonly=True)
    location = fields.Many2one(comodel_name="stock.location", readonly=True)
    initial = fields.Float(readonly=True)
    initial_amount = fields.Float(readonly=True)
    product_in = fields.Float(readonly=True)
    product_in_amount = fields.Float(readonly=True)
    product_out = fields.Float(readonly=True)
    product_out_amount = fields.Float(readonly=True)
    balance = fields.Float(readonly=True)
    amount = fields.Float(readonly=True)

    # TODO: need a field to help these cases more clearly
    # case 1: location set
    #       => count internal transfer and group by location
    #    1.1: group_location = True
    #       => select all child_of location
    #    1.2: group_location = False
    #       => select only location_id
    # case 2: location not set
    #       => select all internal locations
    #    2.1: group_location = True
    #       => count internal transfer and group by location
    #    2.2: group_location = False
    #       => not count internal transfer and neither group by location
    def _get_locations(self, location_id, is_groupby_location):
        count_internal_transfer = True
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
            if not is_groupby_location:
                count_internal_transfer = False
        return locations, count_internal_transfer

    # if leave category blank then select all categories
    # else select all child of category
    def _get_product_category_ids(self, product_category_ids):
        if (product_category_ids):
            product_category_ids = tuple(self.env['product.category'].search(
                [('id', 'child_of', product_category_ids.ids)]).ids)
        else:
            product_category_ids = tuple(
                self.env["product.category"].search([]).ids)
            if not product_category_ids:
                product_category_ids = (-1,)
        return product_category_ids

    # if leave product blank and category blank then select all products
    # else if product blank and not category then select all products child of category
    def _get_product_ids(self, product_ids, product_category_ids):
        if (product_ids):
            product_ids = tuple(product_ids.ids)
        elif (product_category_ids):
            product_ids = tuple(self.env['product.product'].search(
                [('categ_id', 'child_of', product_category_ids.ids)]).ids)
            if not product_ids:
                product_ids = (-1,)
        else:
            product_ids = tuple(self.env["product.product"].search(
                [("active", "=", True)]).ids)
            if not product_ids:
                product_ids = (-1,)
        return product_ids

    # not groupby location: does not care about internal transfer qty
    def _get_internal_picking_type(self, is_groupby_location):
        internal_picking_type = None
        if (not is_groupby_location):
            internal_picking_type = tuple(
                self.env["stock.picking.type"].search([("code", "=", "internal")]).ids)
            if not internal_picking_type:
                internal_picking_type = (-1,)
        return internal_picking_type

    def init_results(self, filter_fields):
        date_from = filter_fields.date_from or "1900-01-01"
        date_to = filter_fields.date_to or fields.Date.context_today(self)
        is_groupby_location = filter_fields.is_groupby_location

        locations, count_internal_transfer = self._get_locations(
            filter_fields.location_id, is_groupby_location)
        product_category_ids = self._get_product_category_ids(
            filter_fields.product_category_ids)
        product_ids = self._get_product_ids(
            filter_fields.product_ids, filter_fields.product_category_ids)
        internal_picking_type = self._get_internal_picking_type(
            is_groupby_location)

        if count_internal_transfer:
            query_ = """
                SELECT *, (a.initial + a.product_in - a.product_out) as balance,
                    (a.initial_amount + a.product_in_amount - a.product_out_amount) as amount
                FROM(
                    SELECT row_number() over () as id,
                        move_group_location.product_id, 
                        move_group_location.product_uom, 
                        move_group_location.location,
                        move_group_location.product_category,
                        (sum(CASE WHEN 
                                CAST(move_group_location.date AS date) < %s 
                                and move_group_location.location = move_group_location.location_dest_id
                            THEN move_group_location.product_qty 
                            ELSE 0 END)
                        -
                        sum(CASE WHEN 
                                CAST(move_group_location.date AS date) < %s 
                                and move_group_location.location = move_group_location.location_id
                            THEN move_group_location.product_qty 
                            ELSE 0 END)) as initial,
                        (sum(CASE WHEN 
                                CAST(move_group_location.date AS date) < %s 
                                and move_group_location.location = move_group_location.location_dest_id
                            THEN move_group_location.product_qty*move_group_location.unit_cost
                            ELSE 0 END)
                        -
                        sum(CASE WHEN 
                                CAST(move_group_location.date AS date) < %s 
                                and move_group_location.location = move_group_location.location_id
                            THEN move_group_location.product_qty*move_group_location.unit_cost
                            ELSE 0 END)) as initial_amount,
                        sum(CASE WHEN 
                                CAST(move_group_location.date AS date) >= %s 
                                and move_group_location.location = move_group_location.location_dest_id
                            THEN move_group_location.product_qty 
                            ELSE 0 END) as product_in,
                        sum(CASE WHEN 
                                CAST(move_group_location.date AS date) >= %s 
                                and move_group_location.location = move_group_location.location_dest_id
                            THEN move_group_location.product_qty*move_group_location.unit_cost
                            ELSE 0 END) as product_in_amount,
                        sum(CASE WHEN 
                                CAST(move_group_location.date AS date) >= %s 
                                and move_group_location.location = move_group_location.location_id
                            THEN move_group_location.product_qty 
                            ELSE 0 END) as product_out,
                        sum(CASE WHEN 
                                CAST(move_group_location.date AS date) >= %s 
                                and move_group_location.location = move_group_location.location_id
                            THEN move_group_location.product_qty*move_group_location.unit_cost
                            ELSE 0 END) as product_out_amount
                    FROM(
                        SELECT 
                            move.date, move.product_id, 
                            move.product_uom,
                            move.location_id as location, 
                            move.location_id, 
                            move.location_dest_id,                        
                            template.categ_id as product_category,
                            move.product_qty,
                            svl.unit_cost
                        FROM stock_move move
                            LEFT JOIN stock_valuation_layer svl 
                                on move.id = svl.stock_move_id
                            LEFT JOIN stock_location location_src 
                                on move.location_id = location_src.id
                            LEFT JOIN product_product product 
                                on move.product_id = product.id
                                LEFT JOIN product_template template 
                                    on product.product_tmpl_id = template.id
                        WHERE 
                            move.location_id in %s
                            and move.state = 'done'
                            and move.product_id in %s
                            and template.categ_id in %s
                            and CAST(move.date AS date) <= %s
                            and location_src.usage = 'internal'
                        UNION ALL
                        SELECT 
                            move.date, move.product_id, 
                            move.product_uom,
                            move.location_dest_id as location, 
                            move.location_id, 
                            move.location_dest_id,
                            template.categ_id as product_category,
                            move.product_qty,
                            svl.unit_cost
                        FROM stock_move move
                            LEFT JOIN stock_valuation_layer svl 
                                on move.id = svl.stock_move_id
                            LEFT JOIN stock_location location_dest 
                                on move.location_dest_id = location_dest.id
                            LEFT JOIN product_product product 
                                on move.product_id = product.id
                                LEFT JOIN product_template template 
                                    on product.product_tmpl_id = template.id
                        WHERE 
                            move.location_dest_id in %s
                            and move.state = 'done'
                            and move.product_id in %s
                            and template.categ_id in %s
                            and CAST(move.date AS date) <= %s
                            and location_dest.usage = 'internal'
                        ) as move_group_location
                    GROUP BY 
                        move_group_location.product_id,
                        move_group_location.product_uom,
                        move_group_location.location,
                        move_group_location.product_category
                    ORDER BY 
                        move_group_location.product_id,
                        move_group_location.product_uom,
                        move_group_location.location,
                        move_group_location.product_category
                    ) as a
            """
            params = (date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      locations,
                      product_ids,
                      product_category_ids,
                      date_to,
                      locations,
                      product_ids,
                      product_category_ids,
                      date_to)
        else:
            query_ = """ 
                SELECT *, (a.initial + a.product_in - a.product_out) as balance,
                    (a.initial_amount + a.product_in_amount - a.product_out_amount) as amount
                FROM(
                    SELECT row_number() over () as id,
                        move.product_id, move.product_uom,
                        null as location,
                        template.categ_id as product_category,
                        (sum(CASE WHEN 
                                CAST(move.date AS date) < %s 
                                and location_dest.usage = 'internal'
                            THEN move.product_qty 
                            ELSE 0 END)
                        -
                        sum(CASE WHEN 
                                CAST(move.date AS date) < %s  
                                and location.usage = 'internal'
                            THEN move.product_qty 
                            ELSE 0 END)) as initial,
                        (sum(CASE WHEN 
                                CAST(move.date AS date) < %s 
                                and location_dest.usage = 'internal'
                            THEN move.product_qty*svl.unit_cost
                            ELSE 0 END)
                        -
                        sum(CASE WHEN 
                                CAST(move.date AS date) < %s  
                                and location.usage = 'internal'
                            THEN move.product_qty*svl.unit_cost 
                            ELSE 0 END)) as initial_amount,
                        sum(CASE WHEN 
                                CAST(move.date AS date) >= %s  
                                and location_dest.usage = 'internal'
                            THEN move.product_qty 
                            ELSE 0 END) as product_in,
                        sum(CASE WHEN 
                                CAST(move.date AS date) >= %s  
                                and location_dest.usage = 'internal'
                            THEN move.product_qty*svl.unit_cost 
                            ELSE 0 END) as product_in_amount,
                        sum(CASE WHEN 
                                CAST(move.date AS date) >= %s  
                                and location.usage = 'internal'
                            THEN move.product_qty 
                            ELSE 0 END) as product_out,
                        sum(CASE WHEN 
                                CAST(move.date AS date) >= %s  
                                and location.usage = 'internal'
                            THEN move.product_qty*svl.unit_cost 
                            ELSE 0 END) as product_out_amount
                    FROM stock_move move
                        LEFT JOIN stock_valuation_layer svl 
                            on move.id = svl.stock_move_id
                        LEFT JOIN stock_location location 
                            on move.location_id = location.id
                        LEFT JOIN stock_location location_dest 
                            on move.location_dest_id = location_dest.id
                        LEFT JOIN product_product product 
                            on move.product_id = product.id
                            LEFT JOIN product_template template 
                                on product.product_tmpl_id = template.id
                    WHERE 
                        (move.location_id in %s or move.location_dest_id in %s)
                        and (move.picking_type_id not in %s or move.picking_type_id is null)
                        and move.state = 'done'
                        and move.product_id in %s
                        and template.categ_id in %s
                        and CAST(move.date AS date) <= %s
                    GROUP BY 
                        move.product_id,
                        move.product_uom,
                        template.categ_id     
                    ORDER BY move.product_id
                    ) as a
                """
            params = (date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      date_from,
                      locations,
                      locations,
                      internal_picking_type,
                      product_ids,
                      product_category_ids,
                      date_to)
        tools.drop_view_if_exists(self._cr, self._table)
        res = self._cr.execute(
            """CREATE VIEW {} as ({})""".format(self._table, query_), params)
        return res

    def report_details(self):
        vals = {}
        filters = self._context.get("filters")
        filters["product_ids"] = [(6, 0, self.product_id.ids)]
        report = self.env["imex.inventory.report.wizard"].create(
            self._context.get("filters"))
        init = self.env["imex.inventory.details.report"].init_results(report)
        details = self.env["imex.inventory.details.report"].search([])
        action = self.env.ref(
            'imex_inventory_report.action_imex_inventory_details_report')
        vals = action.sudo().read()[0]
        context = vals.get("context", {})
        if context:
            context = safe_eval(context)
        context["active_ids"] = details.ids
        data = {
            'product_default_code': report.product_ids.default_code,
            'product_name': report.product_ids.name,
            'date_from': report.date_from or None,
            'date_to': report.date_to or fields.Date.context_today(self),
            'location': report.location_id.complete_name or None,
            'category': report.product_ids.categ_id.complete_name or None,
        }
        context["data"] = data
        vals["context"] = context
        return vals
