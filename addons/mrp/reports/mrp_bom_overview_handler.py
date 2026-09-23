from odoo import models

BOM_OVERVIEW_CARETS = {
    "component": "product.product",
    "bom": "product.product",
    "byproduct": "product.product",
}


class MrpBomOverviewReportHandler(models.AbstractModel):
    _name = "mrp.bom.overview.report.handler"
    _inherit = ["report.formula.custom.handler"]
    _description = "BoM Overview Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        context = self.env.context
        bom_id = (
            context.get("active_id")
            if context.get("active_model") in (None, False, "mrp.bom")
            else None
        ) or previous_options.get("bom_overview_bom_id")
        bom = self.env["mrp.bom"].browse(bom_id).exists()
        options["bom_overview_bom_id"] = bom.id

        options["bom_overview_quantity"] = (
            previous_options.get("bom_overview_quantity") or bom.product_qty or 1
        )
        options["bom_overview_variant_id"] = previous_options.get(
            "bom_overview_variant_id"
        )
        options["bom_overview_variants"] = [
            {"id": variant.id, "name": variant.display_name}
            for variant in bom.product_tmpl_id.product_variant_ids
            if not bom.product_id
        ]
        warehouses = self.env["stock.warehouse"].search(
            self.env["stock.warehouse"]._check_company_domain(self.env.company)
        )
        options["bom_overview_warehouse_id"] = (
            previous_options.get("bom_overview_warehouse_id") or warehouses[:1].id
        )
        options["bom_overview_warehouses"] = [
            {"id": warehouse.id, "name": warehouse.display_name}
            for warehouse in warehouses
        ]
        options["unfold_all"] = previous_options.get("unfold_all", True)
        options["buttons"].append(
            {
                "name": self.env._("Manufacture"),
                "sequence": 5,
                "action": "action_manufacture_from_bom",
                "always_show": True,
            }
        )

    def _caret_options_initializer(self):
        return {
            "product.product": [
                {
                    "name": self.env._("Open Product"),
                    "action": "caret_option_open_record",
                },
                {"name": self.env._("Open Route"), "action": "caret_option_open_route"},
            ],
        }

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        if not options.get("bom_overview_bom_id"):
            return []

        data = (
            self.env["report.mrp.report_bom_structure"]
            .with_context(warehouse_id=options["bom_overview_warehouse_id"])
            ._get_report_data(
                bom_id=options["bom_overview_bom_id"],
                searchQty=options["bom_overview_quantity"],
                searchVariant=options["bom_overview_variant_id"],
            )
        )
        lines = []
        self._collect_lines(report, options, data["lines"], lines)
        return list(enumerate(lines))

    def _collect_lines(self, report, options, row, lines, parent_line_id=None):
        line = self._bom_line(report, options, row, parent_line_id)
        lines.append(line)
        subcontracting = row.get("subcontracting")
        for child in (
            *((subcontracting,) if subcontracting else ()),
            *row.get("components", ()),
            *row.get("operations", ()),
            *row.get("byproducts", ()),
        ):
            self._collect_lines(report, options, child, lines, line["id"])

    def _bom_line(self, report, options, row, parent_line_id=None):
        line_id = report._get_generic_line_id(
            "product.product" if row.get("product_id") else None,
            row.get("product_id") or None,
            markup={"index": str(row.get("index", ""))},
            parent_line_id=parent_line_id,
        )
        currency = self.env["res.currency"].browse(row.get("currency_id"))
        children = (
            row.get("subcontracting")
            or row.get("components")
            or row.get("operations")
            or row.get("byproducts")
        )
        return {
            "id": line_id,
            "parent_id": parent_line_id,
            "name": row.get("name") or "",
            "columns": self._bom_columns(report, options, row, currency),
            "level": (row.get("level") or 0) + 1,
            "unfoldable": bool(children),
            "unfolded": line_id in options["unfolded_lines"] or options["unfold_all"],
            "caret_options": BOM_OVERVIEW_CARETS.get(row.get("type")),
        }

    def _bom_columns(self, report, options, row, currency):
        values = self._bom_row_values(row)
        return [
            report._prepare_column_dict(
                values.get(column["expression_label"]),
                column,
                options=options,
                currency=currency,
            )
            for column in options["columns"]
        ]

    def _bom_row_values(self, row):
        return {
            "quantity": row.get("quantity"),
            "uom": row.get("uom_name") or "",
            "quantity_available": row.get("quantity_available"),
            "status": row.get("status") or "",
            "availability": row.get("availability_display") or "",
            "lead_time": row.get("lead_time"),
            "route": row.get("route_name") or "",
            "bom_cost": row.get("bom_cost"),
        }

    def action_manufacture_from_bom(self, options):
        warehouse = self.env["stock.warehouse"].browse(
            options["bom_overview_warehouse_id"]
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Manufacturing Orders"),
            "res_model": "mrp.production",
            "views": [(False, "form")],
            "target": "current",
            "context": {
                "default_bom_id": options["bom_overview_bom_id"],
                "bom_overview_picking_type_id": warehouse.manu_type_id.id,
                "bom_overview_product_qty": options["bom_overview_quantity"],
            },
        }

    def caret_option_open_record(self, options, params):
        report = self.env["report.formula"].browse(options["report_id"])
        model, record_id = report._get_model_info_from_id(params["line_id"])
        return {
            "type": "ir.actions.act_window",
            "res_model": model,
            "res_id": record_id,
            "views": [(False, "form")],
            "target": "current",
        }

    def caret_option_open_route(self, options, params):
        report = self.env["report.formula"].browse(options["report_id"])
        _model, product_id = report._get_model_info_from_id(params["line_id"])
        product = self.env["product.product"].browse(product_id)
        return self._get_route_action(product)

    def _get_route_action(self, product):
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.product",
            "res_id": product.id,
            "views": [(False, "form")],
            "target": "current",
        }
