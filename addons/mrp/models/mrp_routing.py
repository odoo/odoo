from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL, float_is_zero, float_round

_debug = DebugLog(__name__)


class MrpRoutingWorkcenter(models.Model):
    _name = "mrp.routing.workcenter"
    _description = "Work Center Usage"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.bom.variant.line"]

    _order = "bom_id, sequence, id"
    _check_company_auto = True

    name = fields.Char(
        string="Operation",
        required=True,
    )
    active = fields.Boolean(default=True)
    workcenter_id = fields.Many2one(
        comodel_name="mrp.workcenter",
        string="Work Center",
        index=True,
        required=True,
        check_company=True,
        tracking=True,
    )
    sequence = fields.Integer(
        default=100,
        help="Gives the sequence order when displaying a list of routing Work Centers.",
    )
    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Bill of Material",
        check_company=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        related="bom_id.company_id",
        string="Company",
    )
    archived_with_bom = fields.Boolean(
        help="Technical: this operation was archived because its BoM was, so "
        "unarchiving the BoM brings it back. An operation retired on its own "
        "does not carry the flag and stays retired."
    )
    archived_bom_line_ids = fields.Many2many(
        comodel_name="mrp.bom.line",
        relation="mrp_routing_workcenter_archived_bom_line_rel",
        copy=False,
        help="Technical: bom lines that pointed to this operation before it "
        "was archived, so unarchiving can restore the link.",
    )
    archived_byproduct_ids = fields.Many2many(
        comodel_name="mrp.bom.byproduct",
        relation="mrp_routing_workcenter_archived_byproduct_rel",
        copy=False,
        help="Technical: byproduct lines that pointed to this operation before "
        "it was archived, so unarchiving can restore the link.",
    )
    time_mode = fields.Selection(
        selection=[("manual", "Fixed"), ("auto", "Computed")],
        string="Duration Computation",
        default="manual",
        tracking=True,
    )
    time_mode_batch = fields.Integer(
        string="Based on",
        default=10,
    )
    time_computed_on = fields.Char(
        string="Computed on last",
        compute="_compute_time_computed_on",
    )
    time_cycle_manual = fields.Float(
        string="Manual Duration",
        default=60,
        tracking=True,
        help="Time in minutes:"
        "- In fixed mode, time used"
        "- In computed mode, supposed first time when there aren't any work orders yet",
    )
    time_cycle = fields.Float(
        string="Cycles",
        compute="_compute_operation_times",
    )
    workorder_count = fields.Integer(
        string="# Work Orders",
        compute="_compute_workorder_count",
    )
    workorder_ids = fields.One2many(
        comodel_name="mrp.workorder",
        inverse_name="operation_id",
        string="Work Orders",
    )
    allow_operation_dependencies = fields.Boolean(
        related="bom_id.allow_operation_dependencies"
    )
    blocked_by_operation_ids = fields.Many2many(
        comodel_name="mrp.routing.workcenter",
        relation="mrp_routing_workcenter_dependencies_rel",
        column1="operation_id",
        column2="blocked_by_id",
        string="Blocked By",
        copy=False,
        domain="[('allow_operation_dependencies', '=', True), ('id', '!=', id), ('bom_id', '=', bom_id)]",
        help="Operations that need to be completed before this operation can start.",
    )
    needed_by_operation_ids = fields.Many2many(
        comodel_name="mrp.routing.workcenter",
        relation="mrp_routing_workcenter_dependencies_rel",
        column1="blocked_by_id",
        column2="operation_id",
        string="Blocks",
        copy=False,
        domain="[('allow_operation_dependencies', '=', True), ('id', '!=', id), ('bom_id', '=', bom_id)]",
        help="Operations that cannot start before this operation is completed.",
    )
    cycle_number = fields.Integer(
        string="Repetitions",
        compute="_compute_operation_times",
    )
    time_total = fields.Float(
        string="Total Duration",
        compute="_compute_operation_times",
    )
    show_time_total = fields.Boolean(
        string="Show Total Duration?",
        compute="_compute_operation_times",
    )
    cost_mode = fields.Selection(
        selection=[("actual", "Actual time"), ("estimated", "Theorical time")],
        string="Cost based on",
        default="actual",
        tracking=True,
        help="Determines the way Odoo calculates the cost of the operation:\n"
        "- Based on Actual time: the cost will be calculated based on tracked time and real employee costs.\n"
        "- Based on Estimated time: the cost will be calculated based on estimated time and costs.",
    )
    cost = fields.Float(compute="_compute_cost")

    @api.depends("time_mode", "time_mode_batch")
    def _compute_time_computed_on(self):
        for operation in self:
            operation.time_computed_on = (
                _("%i work orders", operation.time_mode_batch)
                if operation.time_mode != "manual"
                else False
            )

    def _get_recent_workorders(self):
        Workorder = self.env["mrp.workorder"]
        result = {operation.id: Workorder for operation in self}
        if not self:
            return result
        Workorder.flush_model(["operation_id", "qty_produced", "state", "date_end"])
        for batch_size, operations in self.grouped("time_mode_batch").items():
            if batch_size <= 0:
                continue
            query = Workorder._search(
                [
                    ("operation_id", "in", operations.ids),
                    ("qty_produced", ">", 0),
                    ("state", "=", "done"),
                ],
            )
            table = query.table
            ranked = query.select(
                SQL("%s AS id", SQL.identifier(table, "id")),
                SQL("%s AS operation_id", SQL.identifier(table, "operation_id")),
                SQL(
                    "ROW_NUMBER() OVER ("
                    "PARTITION BY %s ORDER BY %s DESC, %s DESC) AS position",
                    SQL.identifier(table, "operation_id"),
                    SQL.identifier(table, "date_end"),
                    SQL.identifier(table, "id"),
                ),
            )
            rows = self.env.execute_query(
                SQL(
                    "SELECT id, operation_id FROM (%s) AS ranked"
                    " WHERE position <= %s ORDER BY operation_id, position",
                    ranked,
                    batch_size,
                ),
            )
            ids_by_operation = defaultdict(list)
            for workorder_id, operation_id in rows:
                ids_by_operation[operation_id].append(workorder_id)
            for operation_id, workorder_ids in ids_by_operation.items():
                result[operation_id] = Workorder.browse(workorder_ids)
            _debug.perf.count(
                "operation_history_ranked",
                batch_size=batch_size,
                operations=len(operations),
                rows=len(rows),
            )
        return result

    @api.depends(
        "time_cycle_manual",
        "time_mode",
        "workorder_ids",
        "bom_id.product_id",
        "bom_id.product_qty",
        "workcenter_id.time_start",
        "workcenter_id.time_stop",
        "workcenter_id.time_efficiency",
        "workcenter_id.capacity_ids",
    )
    @api.depends_context("product", "quantity", "unit", "workcenter")
    def _compute_operation_times(self):
        manual_ops = self.filtered(lambda operation: operation.time_mode == "manual")
        for operation in manual_ops:
            operation.time_cycle = operation.time_cycle_manual
        computed_ops = self - manual_ops
        history = computed_ops._get_recent_workorders()
        for operation in computed_ops:
            total_duration = 0
            cycle_number = 0
            for item in history[operation.id]:
                total_duration += item.duration
                capacity, _setup, _cleanup = item.workcenter_id._get_capacity(
                    item.product_id,
                    item.product_uom_id,
                    operation.bom_id.product_qty or 1,
                )
                cycle_number += float_round(
                    item.qty_produced / capacity,
                    precision_digits=0,
                    rounding_method="UP",
                )
            if cycle_number:
                operation.time_cycle = total_duration / cycle_number
            else:
                operation.time_cycle = operation.time_cycle_manual
            _debug.logic(
                "operation_time_cycle",
                operation=operation.id,
                by="history" if cycle_number else "manual_fallback",
                samples=len(history[operation.id]),
                cycles=cycle_number,
            )

        for operation in self:
            workcenter = self.env.context.get("workcenter", operation.workcenter_id)
            product = self.env.context.get(
                "product", operation.bom_id.product_id
            ) or self.env.context.get(
                "action_button_product",
                operation.bom_id.product_tmpl_id.product_variant_ids.filtered(
                    lambda p, operation=operation: (
                        p.product_template_attribute_value_ids
                        <= operation.bom_product_template_attribute_value_ids
                    )
                ),
            )
            if len(product) > 1:
                product = product[0]
            quantity = self.env.context.get(
                "quantity", operation.bom_id.product_qty or 1
            )
            unit = self.env.context.get("unit", operation.bom_id.product_uom_id)
            if workcenter:
                (capacity, setup, cleanup) = workcenter._get_capacity(
                    product, unit, operation.bom_id.product_qty or 1
                )
            else:
                capacity = operation.bom_id.product_qty or 1
                setup = cleanup = 0.0
            operation.cycle_number = float_round(
                quantity / capacity, precision_digits=0, rounding_method="UP"
            )
            operation.time_total = (
                setup
                + cleanup
                + operation.cycle_number
                * operation.time_cycle
                * 100.0
                / (workcenter.time_efficiency or 100.0)
            )
            operation.show_time_total = operation.cycle_number > 1 or not float_is_zero(
                setup + cleanup, precision_digits=0
            )

    def _compute_workorder_count(self):
        data = self.env["mrp.workorder"]._read_group(
            [("operation_id", "in", self.ids), ("state", "=", "done")],
            ["operation_id"],
            ["__count"],
        )
        count_data = {operation.id: count for operation, count in data}
        for operation in self:
            operation.workorder_count = count_data.get(operation.id, 0)

    @api.depends("time_total", "workcenter_id", "workcenter_id.costs_hour")
    @api.depends_context("product", "quantity", "unit", "workcenter")
    def _compute_cost(self):
        for operation in self:
            operation.cost = (
                operation.time_total / 60.0
            ) * operation.workcenter_id.costs_hour

    @api.constrains("blocked_by_operation_ids")
    def _check_no_cyclic_dependencies(self):
        if self._has_cycle("blocked_by_operation_ids"):
            raise ValidationError(_("You cannot create cyclic dependency."))

    @api.constrains("blocked_by_operation_ids", "bom_id")
    def _check_blocked_by_same_bom(self):
        for operation in self:
            other_boms = operation.blocked_by_operation_ids.bom_id - operation.bom_id
            if other_boms:
                raise ValidationError(
                    _("An operation can only depend on operations of the same BoM.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        _debug.lifecycle("create", operations=res, boms=res.bom_id)
        res.bom_id.with_context(
            skip_bom_outdated_unmark=True
        )._update_outdated_bom_in_productions()
        return res

    _OUTDATING_FIELDS = (
        "workcenter_id",
        "time_mode",
        "time_mode_batch",
        "time_cycle_manual",
        "cost_mode",
        "sequence",
        "bom_id",
        "active",
        "blocked_by_operation_ids",
    )

    def write(self, vals):
        _debug.lifecycle("write", operations=self, fields=list(vals))
        if any(field_name in vals for field_name in self._OUTDATING_FIELDS):
            self.bom_id.with_context(
                skip_bom_outdated_unmark=True
            )._update_outdated_bom_in_productions()
        if "bom_id" in vals:
            for op in self:
                op.bom_id.bom_line_ids.filtered(
                    lambda line, op=op: line.operation_id == op
                ).operation_id = False
                op.bom_id.byproduct_ids.filtered(
                    lambda byproduct, op=op: byproduct.operation_id == op
                ).operation_id = False
                op.bom_id.operation_ids.filtered(
                    lambda operation, op=op: op in operation.blocked_by_operation_ids
                ).blocked_by_operation_ids = [Command.unlink(op.id)]
        return super().write(vals)

    def action_archive(self):
        res = super().action_archive()
        bom_lines = self.env["mrp.bom.line"].search([("operation_id", "in", self.ids)])
        byproduct_lines = self.env["mrp.bom.byproduct"].search(
            [("operation_id", "in", self.ids)]
        )
        for op, lines in bom_lines.grouped("operation_id").items():
            op.archived_bom_line_ids = lines
        for op, lines in byproduct_lines.grouped("operation_id").items():
            op.archived_byproduct_ids = lines
        _debug.lifecycle(
            "operation_archived",
            operations=self,
            bom_lines=len(bom_lines),
            byproducts=len(byproduct_lines),
        )
        bom_lines.write({"operation_id": False})
        byproduct_lines.write({"operation_id": False})
        self.bom_id.with_context(
            skip_bom_outdated_unmark=True
        )._update_outdated_bom_in_productions()
        return res

    def action_unarchive(self):
        res = super().action_unarchive()
        for op in self:
            op.archived_bom_line_ids.write({"operation_id": op.id})
            op.archived_byproduct_ids.write({"operation_id": op.id})
        _debug.lifecycle("operation_unarchived", operations=self)
        self.archived_bom_line_ids = [Command.clear()]
        self.archived_byproduct_ids = [Command.clear()]
        self.bom_id.with_context(
            skip_bom_outdated_unmark=True
        )._update_outdated_bom_in_productions()
        return res

    def action_copy_to_bom(self):
        if "bom_id" in self.env.context:
            bom_id = self.env.context.get("bom_id")
            for operation in self:
                operation.copy({"bom_id": bom_id})
            return {
                "view_mode": "form",
                "res_model": "mrp.bom",
                "views": [(False, "form")],
                "type": "ir.actions.act_window",
                "res_id": bom_id,
            }
        return None

    def action_copy_existing_operations(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Select Operations to Copy"),
            "res_model": "mrp.routing.workcenter",
            "view_mode": "list,form",
            "domain": ["|", ("bom_id", "=", False), ("bom_id.active", "=", True)],
            "context": {
                "bom_id": self.env.context["bom_id"],
                "list_view_ref": "mrp.mrp_routing_workcenter_copy_to_bom_tree_view",
            },
        }

    def _is_bom_line_skipped(self, product, never_attribute_values=False):
        self.check_singleton()
        if not self.active:
            return True
        return super()._is_bom_line_skipped(product, never_attribute_values)

    def action_view_operation_form(self):
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mrp.routing.workcenter",
        }
