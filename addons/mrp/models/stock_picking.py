from ast import literal_eval
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    code = fields.Selection(
        selection_add=[("mrp_operation", "Manufacturing")],
        ondelete={
            "mrp_operation": lambda recs: recs.write(
                {"code": "incoming", "active": False}
            )
        },
    )
    count_mo_todo = fields.Integer(
        string="Number of Manufacturing Orders to Process",
        compute="_compute_mo_counts",
    )
    count_mo_waiting = fields.Integer(
        string="Number of Manufacturing Orders Waiting",
        compute="_compute_mo_counts",
    )
    count_mo_late = fields.Integer(
        string="Number of Manufacturing Orders Late",
        compute="_compute_mo_counts",
    )
    count_mo_in_progress = fields.Integer(
        string="Number of Manufacturing Orders In Progress",
        compute="_compute_mo_counts",
    )
    count_mo_to_close = fields.Integer(
        string="Number of Manufacturing Orders To Close",
        compute="_compute_mo_counts",
    )
    use_create_components_lots = fields.Boolean(
        string="Create New Lots/Serial Numbers for Components",
        default=False,
        help="Allow to create new lot/serial numbers for the components",
    )

    auto_print_done_production_order = fields.Boolean(
        help="If this checkbox is ticked, Odoo will automatically print the production order of a MO when it is done."
    )
    auto_print_done_mrp_product_labels = fields.Boolean(
        string="Auto Print Produced Product Labels",
        help="If this checkbox is ticked, Odoo will automatically print the product labels of a MO when it is done.",
    )
    mrp_product_label_to_print = fields.Selection(
        selection=[("pdf", "PDF"), ("zpl", "ZPL")],
        string="Product Label to Print",
        default="pdf",
    )
    auto_print_done_mrp_lot = fields.Boolean(
        string="Auto Print Produced Lot Label",
        help="If this checkbox is ticked, Odoo will automatically print the lot/SN label of a MO when it is done.",
    )
    done_mrp_lot_label_to_print = fields.Selection(
        selection=[("pdf", "PDF"), ("zpl", "ZPL")],
        string="Lot/SN Label to Print",
        default="pdf",
    )
    auto_print_mrp_reception_report = fields.Boolean(
        string="Auto Print Allocation Report",
        help="If this checkbox is ticked, Odoo will automatically print the allocation report of a MO when it is done and has assigned moves.",
    )
    auto_print_mrp_reception_report_labels = fields.Boolean(
        string="Auto Print Allocation Report Labels",
        help="If this checkbox is ticked, Odoo will automatically print the allocation report labels of a MO when it is done.",
    )
    auto_print_generated_mrp_lot = fields.Boolean(
        string="Auto Print Generated Lot/SN Label",
        help='Automatically print the lot/SN label when the "Create a new serial/lot number" button is used.',
    )
    generated_mrp_lot_label_to_print = fields.Selection(
        selection=[("pdf", "PDF"), ("zpl", "ZPL")],
        string="Generated Lot/SN Label to Print",
        default="pdf",
    )

    @api.depends("code")
    def _compute_use_create_lots(self):
        super()._compute_use_create_lots()
        for picking_type in self:
            if picking_type.code == "mrp_operation":
                picking_type.use_create_lots = True

    @api.depends("code")
    def _compute_use_existing_lots(self):
        super()._compute_use_existing_lots()
        for picking_type in self:
            if picking_type.code == "mrp_operation":
                picking_type.use_existing_lots = True

    @api.constrains("default_location_dest_id")
    def _check_default_location(self):
        for record in self:
            if (
                record.code == "mrp_operation"
                and record.default_location_dest_id.usage == "inventory"
            ):
                raise ValidationError(
                    _(
                        "You cannot set a scrap location as the destination location for a manufacturing type operation."
                    )
                )

    @api.depends("code")
    def _compute_mo_counts(self):
        mrp_picking_types = self.filtered(
            lambda picking: picking.code == "mrp_operation"
        )
        remaining = self - mrp_picking_types
        remaining.count_mo_waiting = remaining.count_mo_todo = (
            remaining.count_mo_late
        ) = False
        remaining.count_mo_in_progress = remaining.count_mo_to_close = False
        if not mrp_picking_types:
            return
        _debug.perf.count("mo_counts_computed", picking_types=mrp_picking_types)
        counts_by_state = defaultdict(lambda: defaultdict(int))
        for picking_type, state, count in self.env["mrp.production"]._read_group(
            [
                ("state", "not in", ("done", "cancel")),
                ("picking_type_id", "in", mrp_picking_types.ids),
            ],
            ["picking_type_id", "state"],
            ["__count"],
        ):
            counts_by_state[picking_type.id][state] = count
        waiting = {
            picking_type.id: count
            for picking_type, count in self.env["mrp.production"]._read_group(
                [
                    ("state", "not in", ("done", "cancel")),
                    ("reservation_state", "=", "waiting"),
                    ("picking_type_id", "in", mrp_picking_types.ids),
                ],
                ["picking_type_id"],
                ["__count"],
            )
        }
        late = {
            picking_type.id: count
            for picking_type, count in self.env["mrp.production"]._read_group(
                [
                    ("state", "=", "confirmed"),
                    ("date_start", "<", fields.Date.today()),
                    ("picking_type_id", "in", mrp_picking_types.ids),
                ],
                ["picking_type_id"],
                ["__count"],
            )
        }
        for record in mrp_picking_types:
            by_state = counts_by_state[record.id]
            record.count_mo_todo = by_state["confirmed"]
            record.count_mo_in_progress = by_state["progress"]
            record.count_mo_to_close = by_state["to_close"]
            record.count_mo_waiting = waiting.get(record.id, 0)
            record.count_mo_late = late.get(record.id, 0)

    def action_view_productions(self):
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.mrp_production_action_picking_deshboard"
        )
        if self:
            action["display_name"] = self.display_name
        return action

    def _get_aggregated_records_by_date(self):
        production_picking_types = self.filtered(
            lambda picking: picking.code == "mrp_operation"
        )
        other_picking_types = self - production_picking_types

        records = super(
            StockPickingType, other_picking_types
        )._get_aggregated_records_by_date()
        counts_by_type = production_picking_types._get_date_category_counts(
            "mrp.production",
            "date_start",
            "picking_type_id",
            [("state", "=", "confirmed")],
        )
        label = self.env._("Confirmed")
        return records + [
            (picking_type_id, counts, label)
            for picking_type_id, counts in counts_by_type.items()
        ]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    has_kits = fields.Boolean(compute="_compute_has_kits")
    production_count = fields.Integer(
        string="Count of MO generated",
        compute="_compute_production_count",
        groups="mrp.group_mrp_user",
    )

    production_ids = fields.One2many(
        comodel_name="mrp.production",
        string="Manufacturing Orders",
        compute="_compute_production_ids",
        groups="mrp.group_mrp_user",
    )

    @api.depends("move_ids")
    def _compute_has_kits(self):
        for picking in self:
            picking.has_kits = any(picking.move_ids.mapped("bom_line_id"))

    @api.depends("move_ids.production_group_id.production_ids")
    def _compute_production_ids(self):
        for picking in self:
            picking.production_ids = picking.move_ids.production_group_id.production_ids

    @api.depends("production_ids")
    def _compute_production_count(self):
        for picking in self:
            mo = picking.production_ids.filtered(lambda mo: mo.picking_type_id.active)
            picking.production_count = len(mo)

    def action_detailed_operations(self):
        action = super().action_detailed_operations()
        action["context"]["has_kits"] = self.has_kits
        return action

    def action_view_mrp_production(self):
        self.check_singleton()
        action = {
            "name": _("Manufacturing Orders"),
            "res_model": "mrp.production",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", self.production_ids.ids)],
            "view_mode": "list,form",
        }
        if self.production_count == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": self.production_ids.id,
                }
            )
        return action

    def _add_less_quantities_than_expected_documents(self, moves, documents):
        documents = super()._add_less_quantities_than_expected_documents(
            moves, documents
        )

        def get_groupby_key(move):
            return (move.raw_material_production_id, move.product_id.responsible_id)

        production_documents = self._get_log_activity_documents(
            moves, "move_dest_ids", "DOWN", get_groupby_key
        )
        return {**documents, **production_documents}

    @api.model
    def get_action_click_graph(self):
        picking_type_id = self.env.context["picking_type_id"]
        picking_type_code = self.env["stock.picking.type"].browse(picking_type_id).code

        if picking_type_code == "mrp_operation":
            action = self._prepare_action_by_xml_id(
                "mrp.action_picking_tree_mrp_operation_graph"
            )
            action["domain"] = Domain.AND(
                [
                    literal_eval(action["domain"] or "[]"),
                    [("picking_type_id", "=", picking_type_id)],
                ]
            )
            allowed_company_ids = self.env.context.get("allowed_company_ids", [])
            if allowed_company_ids:
                action["context"].update(
                    {
                        "default_company_id": allowed_company_ids[0],
                    }
                )
            return action

        return super().get_action_click_graph()
