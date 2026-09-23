from collections import deque

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import format_datetime

from ..tools import debug_log as dbg


class StockTraceabilityReport(models.TransientModel):
    _name = "stock.traceability.report"
    _description = "Traceability Report"

    @api.model
    def _get_move_lines(self, move_lines, line_id=None):
        lines_seen = move_lines
        lines_todo = deque(move_lines)
        while lines_todo:
            move_line = lines_todo.popleft()
            if move_line.move_id.move_orig_ids:
                lines = (
                    move_line.move_id.move_orig_ids.move_line_ids.filtered(
                        lambda m, lot=move_line.lot_id: (
                            m.lot_id == lot and m.state == "done"
                        )
                    )
                    - lines_seen
                )
            elif move_line.location_id.usage in ("internal", "transit"):
                lines = self.env["stock.move.line"].search(
                    [
                        ("product_id", "=", move_line.product_id.id),
                        ("lot_id", "=", move_line.lot_id.id),
                        ("location_dest_id", "=", move_line.location_id.id),
                        ("id", "not in", lines_seen.ids),
                        ("date", "<=", move_line.date),
                        ("state", "=", "done"),
                    ]
                )
            else:
                continue
            if line_id is None:
                lines_todo.extend(lines)
            lines_seen |= lines
        return lines_seen - move_lines

    @api.model
    def _has_upstream_move_lines(self, move_line):
        if move_line.move_id.move_orig_ids:
            return bool(
                move_line.move_id.move_orig_ids.move_line_ids.filtered(
                    lambda m: m.lot_id == move_line.lot_id and m.state == "done"
                )
                - move_line
            )
        if move_line.location_id.usage in ("internal", "transit"):
            return bool(
                self.env["stock.move.line"].search(
                    [
                        ("product_id", "=", move_line.product_id.id),
                        ("lot_id", "=", move_line.lot_id.id),
                        ("location_dest_id", "=", move_line.location_id.id),
                        ("id", "!=", move_line.id),
                        ("date", "<=", move_line.date),
                        ("state", "=", "done"),
                    ],
                    limit=1,
                )
            )
        return False

    @dbg.timed
    @api.model
    def get_lines(self, line_id=False, **kw):
        context = self.env.context
        model = kw.get("model_name") or context.get("model")
        rec_id = kw.get("model_id") or context.get("active_id")
        level = kw.get("level") or 1
        move_lines = self.env["stock.move.line"]
        if model and model not in self._get_models_allowed_line():
            dbg.logic.debug("traceability get_lines: model %s not allowed", model)
            return []
        if rec_id and model == "stock.lot":
            move_lines = move_lines.search(
                [
                    ("lot_id", "=", context.get("lot_name") or rec_id),
                    ("state", "=", "done"),
                ]
            )
        elif rec_id and model == "stock.move.line" and context.get("lot_name"):
            is_used = self._get_linked_move_lines(self.env[model].browse(rec_id))[1]
            if is_used:
                move_lines = is_used
        elif rec_id and model in ("stock.picking", "mrp.production"):
            record = self.env[model].browse(rec_id)
            if model == "stock.picking":
                move_lines = record.move_ids.move_line_ids.filtered(
                    lambda m: m.lot_id and m.state == "done"
                )
            else:
                move_lines = record.move_finished_ids.move_line_ids.filtered(
                    lambda m: m.state == "done"
                )
        dbg.logic.debug(
            "traceability get_lines model=%s id=%s level=%s line_id=%s: %d move lines",
            model,
            rec_id,
            level,
            line_id,
            len(move_lines),
        )
        vals = self._prepare_traceability_lines(
            line_id, model_id=rec_id, model=model, level=level, move_lines=move_lines
        )
        vals.sort(key=lambda v: v["date"], reverse=True)
        return self._final_vals_to_lines(vals)

    @api.model
    def _get_reference(self, move_line):
        res_model = ""
        res_id = False
        ref = ""
        picking_id = move_line.picking_id or move_line.move_id.picking_id
        if picking_id:
            res_model = "stock.picking"
            res_id = picking_id.id
            ref = picking_id.name
        elif move_line.move_id.is_inventory:
            res_model = "stock.move"
            res_id = move_line.move_id.id
            ref = self.env._("Inventory Adjustment")
        elif (
            move_line.move_id.location_dest_usage == "inventory"
            and move_line.move_id.scrap_id
        ):
            res_model = "stock.scrap"
            res_id = move_line.move_id.scrap_id.id
            ref = move_line.move_id.scrap_id.name
        return res_model, res_id, ref

    @api.model
    def _quantity_to_str(self, from_uom, to_uom, qty):
        qty = from_uom._get_quantity_report(qty, to_uom, rounding_method="HALF-UP")
        return self.env["ir.qweb.field.float"].value_to_html(
            qty, {"decimal_precision": "Product Unit"}
        )

    @api.model
    def _get_usage(self, move_line):
        source_internal = move_line.location_id.usage == "internal"
        dest_internal = move_line.location_dest_id.usage == "internal"
        if source_internal and dest_internal:
            return "internal"
        if dest_internal:
            return "in"
        return "out"

    @api.model
    def _get_names_source_destination(self, move_line):
        source_name = move_line.location_id.display_name
        destination_name = move_line.location_dest_id.display_name
        partner_name = move_line.picking_partner_id.name
        picking_code = move_line.picking_id.picking_type_code
        if picking_code == "incoming":
            return partner_name, destination_name
        if picking_code == "outgoing":
            return source_name, partner_name
        return source_name, destination_name

    @api.model
    def _prepare_dict_move(self, level, parent_id, move_line, unfoldable=False):
        res_model, res_id, ref = self._get_reference(move_line)
        is_used = self._get_linked_move_lines(move_line)[1]
        location_source, location_destination = self._get_names_source_destination(
            move_line
        )
        return {
            "level": level,
            "unfoldable": unfoldable,
            "date": move_line.move_id.date,
            "parent_id": parent_id,
            "is_used": bool(is_used),
            "usage": self._get_usage(move_line),
            "model_id": move_line.id,
            "model": "stock.move.line",
            "product_id": move_line.product_id.display_name,
            "product_qty_uom": "%s %s"
            % (
                self._quantity_to_str(
                    move_line.product_uom_id,
                    move_line.product_id.uom_id,
                    move_line.quantity,
                ),
                move_line.product_id.uom_id.name,
            ),
            "lot_name": move_line.lot_id.name,
            "lot_id": move_line.lot_id.id,
            "location_source": location_source,
            "location_destination": location_destination,
            "partner_id": move_line.picking_partner_id.id,
            "picking_type_code": move_line.picking_id.picking_type_code,
            "reference_id": ref,
            "res_id": res_id,
            "res_model": res_model,
        }

    @api.model
    def _final_vals_to_lines(self, final_vals):
        return [
            {
                "id": counter,
                "model": data["model"],
                "model_id": data["model_id"],
                "parent_id": data["parent_id"],
                "usage": data["usage"],
                "is_used": data["is_used"],
                "lot_name": data["lot_name"],
                "lot_id": data["lot_id"],
                "reference": data["reference_id"],
                "location_source": data["location_source"],
                "location_destination": data["location_destination"],
                "partner_id": data["partner_id"],
                "picking_type_code": data["picking_type_code"],
                "res_id": data["res_id"],
                "res_model": data["res_model"],
                "columns": [
                    data["reference_id"],
                    data["product_id"],
                    format_datetime(self.env, data["date"], tz=False, dt_format=False),
                    data["lot_name"],
                    data["location_source"],
                    data["location_destination"],
                    data["product_qty_uom"],
                ],
                "level": data["level"],
                "unfoldable": data["unfoldable"],
            }
            for counter, data in enumerate(final_vals, start=1)
        ]

    @api.model
    def _get_linked_move_lines(self, move_line):
        return False, False

    @api.model
    def _prepare_traceability_lines(
        self, line_id=False, model_id=False, model=False, level=0, move_lines=None
    ):
        final_vals = []
        lines = move_lines or self.env["stock.move.line"]
        if model and line_id:
            if model not in self._get_models_allowed_line():
                return final_vals
            move_line = self.env[model].browse(model_id)
            linked_lines = self._get_linked_move_lines(move_line)[0]
            if linked_lines:
                lines = linked_lines
            else:
                lines = self._get_move_lines(move_line, line_id=line_id)
        for line in lines:
            unfoldable = bool(
                line.consume_line_ids
                or (
                    model != "stock.lot"
                    and line.lot_id
                    and self._has_upstream_move_lines(line)
                )
            )
            final_vals.append(
                self._prepare_dict_move(
                    level, parent_id=line_id, move_line=line, unfoldable=unfoldable
                )
            )
        return final_vals

    @api.model
    def _get_models_allowed_line(self):
        return {"stock.lot", "stock.move.line", "stock.picking"}


TRACEABILITY_COLUMNS = (
    "reference",
    "product",
    "date",
    "lot",
    "location_source",
    "location_destination",
    "quantity",
)


class StockTraceabilityReportHandler(models.AbstractModel):
    _name = "stock.traceability.report.handler"
    _inherit = ["report.formula.custom.handler"]
    _description = "Traceability Report Custom Handler"

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)
        context = self.env.context
        if context.get("active_id"):
            target = {
                "model": context.get("active_model") or context.get("model") or False,
                "id": context["active_id"],
                "lot_name": context.get("lot_name") or False,
            }
        else:
            target = previous_options.get("traceability") or {
                "model": False,
                "id": False,
                "lot_name": False,
            }
        options["traceability"] = target
        if context.get("auto_unfold"):
            options["unfold_all"] = True

    def _caret_options_initializer(self):
        return {
            "stock.move.line": [
                {
                    "name": self.env._("Open Reference"),
                    "action": "caret_option_open_traceability_reference",
                },
                {
                    "name": self.env._("Open Lot/Serial Number"),
                    "action": "caret_option_open_traceability_lot",
                },
                {
                    "name": self.env._("Open Partner"),
                    "action": "caret_option_open_traceability_partner",
                },
                {
                    "name": self.env._("Upstream and Downstream"),
                    "action": "caret_option_open_traceability_stream",
                },
            ],
        }

    def _dynamic_lines_generator(
        self, report, options, all_column_groups_expression_totals, warnings=None
    ):
        target = options["traceability"]
        rows = (
            self.env["stock.traceability.report"]
            .with_context(
                model=target["model"],
                active_id=target["id"],
                lot_name=target["lot_name"],
            )
            .get_lines()
        )
        return [(0, self._traceability_line(report, options, row)) for row in rows]

    def _report_expand_unfoldable_line_traceability(
        self,
        line_dict_id,
        groupby,
        options,
        progress,
        offset,
        unfold_all_batch_data=None,
    ):
        report = self.env["report.formula"].browse(options["report_id"])
        _markup, model, record_id = report._parse_line_id(line_dict_id)[-1]
        rows = self.env["stock.traceability.report"].get_lines(
            record_id, model_name=model, model_id=record_id
        )
        lines = [
            self._traceability_line(report, options, row, parent_line_id=line_dict_id)
            for row in rows
        ]
        return {
            "lines": lines,
            "offset_increment": len(lines),
            "has_more": False,
            "progress": progress,
        }

    def _traceability_line(self, report, options, row, parent_line_id=None):
        line_id = report._get_generic_line_id(
            row["model"], row["model_id"], parent_line_id=parent_line_id
        )
        values = dict(zip(TRACEABILITY_COLUMNS, row["columns"], strict=True))
        return {
            "id": line_id,
            "parent_id": parent_line_id,
            "name": values["reference"] or "",
            "columns": [
                report._prepare_column_dict(
                    values[column["expression_label"]], column, options=options
                )
                for column in options["columns"]
            ],
            "level": sum(
                model == "stock.move.line"
                for _markup, model, _id in report._parse_line_id(line_id)
            ),
            "unfoldable": row["unfoldable"],
            "unfolded": line_id in options["unfolded_lines"] or options["unfold_all"],
            "expand_function": "_report_expand_unfoldable_line_traceability",
            "caret_options": "stock.move.line",
        }

    def _clicked_move_line(self, options, params):
        report = self.env["report.formula"].browse(options["report_id"])
        model, record_id = report._get_model_info_from_id(params["line_id"])
        if model != "stock.move.line":
            return self.env["stock.move.line"]
        return self.env["stock.move.line"].browse(record_id)

    def _form_action(self, record, message):
        if not record:
            raise UserError(message)
        return {
            "type": "ir.actions.act_window",
            "res_model": record._name,
            "res_id": record.id,
            "views": [(False, "form")],
            "target": "current",
        }

    def caret_option_open_traceability_reference(self, options, params):
        move_line = self._clicked_move_line(options, params)
        res_model, res_id, _reference = self.env[
            "stock.traceability.report"
        ]._get_reference(move_line)
        record = self.env[res_model].browse(res_id) if res_model else move_line.browse()
        return self._form_action(
            record, self.env._("This operation has no reference to open.")
        )

    def caret_option_open_traceability_lot(self, options, params):
        move_line = self._clicked_move_line(options, params)
        return self._form_action(
            move_line.lot_id,
            self.env._("This operation moves no lot or serial number."),
        )

    def caret_option_open_traceability_partner(self, options, params):
        move_line = self._clicked_move_line(options, params)
        return self._form_action(
            move_line.picking_partner_id, self.env._("This operation has no partner.")
        )

    def caret_option_open_traceability_stream(self, options, params):
        move_line = self._clicked_move_line(options, params)
        return {
            "type": "ir.actions.client",
            "tag": "account_report",
            "name": self.env._("Traceability Report"),
            "context": {
                "report_id": options["report_id"],
                "active_id": move_line.id,
                "active_model": "stock.move.line",
                "lot_name": move_line.lot_id.name or False,
                "auto_unfold": True,
            },
        }
