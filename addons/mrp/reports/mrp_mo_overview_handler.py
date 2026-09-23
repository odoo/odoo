from odoo import models

STATE_DECORATORS = {
    "mrp.production": {
        "draft": "secondary",
        "confirmed": "info",
        "progress": "warning",
        "done": "success",
        "to_close": "success",
        "cancel": "danger",
    },
    "mrp.workorder": {
        "blocked": "warning",
        "ready": "muted",
        "progress": "info",
        "done": "success",
        "cancel": "danger",
    },
    "stock.picking": {
        "draft": "secondary",
        "waiting": "warning",
        "confirmed": "warning",
        "assigned": "info",
        "done": "success",
        "cancel": "danger",
    },
    "purchase.order": {"draft": "info", "done": "info", "cancel": "secondary"},
    "product.product": {"to_order": "danger"},
}

MO_OVERVIEW_CARETS = {
    "mrp.production": "mrp.production",
    "product.product": "product.product",
}


class MrpMoOverviewReportHandler(models.AbstractModel):
    _name = "mrp.mo.overview.report.handler"
    _inherit = ["report.formula.custom.handler"]
    _description = "MO Overview Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        context = self.env.context
        production_id = (
            context.get("active_id")
            if context.get("active_model") in (False, "mrp.production")
            else None
        ) or previous_options.get("mo_overview_production_id")
        options["mo_overview_production_id"] = production_id
        options["unfold_all"] = previous_options.get("unfold_all", True)

    def _caret_options_initializer(self):
        return {
            "mrp.production": [
                {
                    "name": self.env._("Open Manufacturing Order"),
                    "action": "caret_option_open_record",
                },
            ],
            "product.product": [
                {
                    "name": self.env._("Open Product"),
                    "action": "caret_option_open_record",
                },
            ],
        }

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        production_id = options.get("mo_overview_production_id")
        if not production_id:
            return []

        data = self.env["report.mrp.report_mo_overview"]._get_report_data(production_id)
        lines = [self._overview_line(report, options, data["summary"])]
        summary_id = lines[0]["id"]

        for component in data["components"]:
            component_line = self._overview_line(
                report,
                options,
                component["summary"],
                parent_line_id=summary_id,
                unfoldable=bool(component["replenishments"]),
            )
            lines.append(component_line)
            lines.extend(
                self._overview_line(
                    report,
                    options,
                    replenishment["summary"],
                    parent_line_id=component_line["id"],
                )
                for replenishment in component["replenishments"]
            )

        for block in (data["operations"], data["byproducts"]):
            lines.extend(self._block_lines(report, options, block, summary_id))

        lines.extend(self._extra_lines(report, options, data))
        return list(enumerate(lines))

    def _block_lines(self, report, options, block, parent_line_id):
        if not block or not block.get("details"):
            return []

        lines = [
            self._overview_line(
                report,
                options,
                block["summary"],
                parent_line_id=parent_line_id,
                unfoldable=True,
            )
        ]
        block_id = lines[0]["id"]
        lines.extend(
            self._overview_line(report, options, detail, parent_line_id=block_id)
            for detail in block["details"]
        )
        return lines

    def _extra_lines(self, report, options, data):
        extras = data["extras"]
        summary = data["summary"]
        rows = [
            (
                self.env._("Unit Cost"),
                {
                    "mo_cost": extras.get("unit_mo_cost"),
                    "bom_cost": extras.get("unit_bom_cost"),
                    "real_cost": extras.get("unit_real_cost"),
                },
            )
        ]
        if "total_mo_cost" in extras:
            rows += [
                (
                    self.env._("Total Cost of Components"),
                    {
                        "mo_cost": extras["total_mo_cost_components"],
                        "bom_cost": extras["total_bom_cost_components"],
                        "real_cost": extras["total_real_cost_components"],
                    },
                ),
                (
                    self.env._("Total Cost of Operations"),
                    {
                        "mo_cost": extras["total_mo_cost_operations"],
                        "bom_cost": extras["total_bom_cost_operations"],
                        "real_cost": extras["total_real_cost_operations"],
                    },
                ),
                (
                    self.env._("Total Cost"),
                    {
                        "mo_cost": extras["total_mo_cost"],
                        "bom_cost": extras["total_bom_cost"],
                        "real_cost": extras["total_real_cost"],
                    },
                ),
            ]

        currency = self.env["res.currency"].browse(summary.get("currency_id"))
        return [
            {
                "id": report._get_generic_line_id(None, None, markup={"total": name}),
                "name": name,
                "columns": self._overview_columns(report, options, values, currency),
                "level": 0,
                "class": "total",
            }
            for name, values in rows
        ]

    def _overview_line(
        self, report, options, row, parent_line_id=None, unfoldable=False
    ):
        line_id = report._get_generic_line_id(
            row.get("model") or None,
            row.get("id") or None,
            markup={"index": row.get("index") or ""},
            parent_line_id=parent_line_id,
        )
        currency = self.env["res.currency"].browse(row.get("currency_id"))
        return {
            "id": line_id,
            "parent_id": parent_line_id,
            "name": row.get("name") or "",
            "columns": self._overview_columns(report, options, row, currency),
            "level": row.get("level", 0) + 1,
            "unfoldable": unfoldable,
            "unfolded": line_id in options["unfolded_lines"] or options["unfold_all"],
            "caret_options": MO_OVERVIEW_CARETS.get(row.get("model")),
        }

    def _overview_columns(self, report, options, row, currency):
        values = {
            "status": row.get("formatted_state") or "",
            "quantity": row.get("quantity"),
            "uom": row.get("uom_name") or "",
            "quantity_free": row.get("quantity_free"),
            "quantity_reserved": row.get("quantity_reserved"),
            "receipt": (row.get("receipt") or {}).get("display") or "",
            "unit_cost": row.get("unit_cost"),
            "mo_cost": row.get("mo_cost"),
            "bom_cost": row.get("bom_cost"),
            "real_cost": row.get("real_cost"),
        }
        state_decorator = STATE_DECORATORS.get(row.get("model"), {}).get(
            row.get("state")
        )
        decorators = {
            "status": f"bg-{state_decorator}" if state_decorator else False,
            "mo_cost": row.get("mo_cost_decorator"),
            "real_cost": row.get("real_cost_decorator"),
            "receipt": (row.get("receipt") or {}).get("decorator"),
        }
        columns = []
        for column in options["columns"]:
            label = column["expression_label"]
            value = values.get(label)
            cell = report._prepare_column_dict(
                value, column, options=options, currency=currency
            )
            decorator = decorators.get(label)
            if decorator:
                cell = {**cell, "class": f"text-{decorator}"}
            columns.append(cell)
        return columns

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


class MrpMoCostBreakdownReportHandler(models.AbstractModel):
    _name = "mrp.mo.cost.breakdown.report.handler"
    _inherit = ["mrp.mo.overview.report.handler"]
    _description = "MO Cost Breakdown Custom Handler"

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        production_id = options.get("mo_overview_production_id")
        if not production_id:
            return []

        data = self.env["report.mrp.report_mo_overview"]._get_report_data(production_id)
        currency = self.env["res.currency"].browse(data["summary"].get("currency_id"))
        return [
            (
                index,
                {
                    "id": report._get_generic_line_id(
                        None, None, markup={"breakdown": row["index"]}
                    ),
                    "name": row["name"],
                    "columns": [
                        report._prepare_column_dict(
                            row.get(column["expression_label"])
                            if column["expression_label"] != "uom"
                            else row["uom_name"],
                            column,
                            options=options,
                            currency=currency,
                        )
                        for column in options["columns"]
                    ],
                    "level": 1,
                },
            )
            for index, row in enumerate(data["cost_breakdown"])
        ]
