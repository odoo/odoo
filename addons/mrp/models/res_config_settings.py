from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_mrp_byproducts = fields.Boolean(
        string="By-Products",
        implied_group="mrp.group_mrp_byproducts",
    )
    module_mrp_mps = fields.Boolean(string="Master Production Schedule")
    module_mrp_plm = fields.Boolean(string="Product Lifecycle Management (PLM)")
    module_quality_control = fields.Boolean(string="Quality")
    module_quality_control_worksheet = fields.Boolean(string="Quality Worksheet")
    module_mrp_subcontracting = fields.Boolean(string="Subcontracting")
    group_mrp_routings = fields.Boolean(
        string="MRP Work Orders",
        implied_group="mrp.group_mrp_routings",
    )
    group_unlocked_by_default = fields.Boolean(
        string="Unlock Manufacturing Orders",
        implied_group="mrp.group_unlocked_by_default",
    )
    group_mrp_reception_report = fields.Boolean(
        string="Allocation Report for Manufacturing Orders",
        implied_group="mrp.group_mrp_reception_report",
    )
    group_mrp_workorder_dependencies = fields.Boolean(
        string="Work Order Dependencies",
        implied_group="mrp.group_mrp_workorder_dependencies",
    )

    def set_values(self):
        routing_before = self.env.user.has_group("mrp.group_mrp_routings")
        super().set_values()
        if routing_before and not self.group_mrp_routings:
            self.env["mrp.routing.workcenter"].search([]).active = False
        elif not routing_before and self.group_mrp_routings:
            operations = self.env["mrp.routing.workcenter"].search_read(
                [("active", "=", False)], ["id", "write_date"]
            )
            last_updated = max((op["write_date"] for op in operations), default=0)
            if last_updated:
                op_to_update = self.env["mrp.routing.workcenter"].browse(
                    [op["id"] for op in operations if op["write_date"] == last_updated]
                )
                op_to_update.active = True
        if not self.group_mrp_workorder_dependencies:
            self.env["mrp.bom"].sudo().search(
                [("allow_operation_dependencies", "=", True)]
            ).allow_operation_dependencies = False

    @api.onchange("group_unlocked_by_default")
    def _onchange_group_unlocked_by_default(self):
        if self.group_unlocked_by_default:
            self.env["mrp.production"].search(
                [("state", "not in", ("cancel", "done")), ("is_locked", "=", True)]
            ).is_locked = False
        else:
            self.env["mrp.production"].search(
                [("state", "not in", ("cancel", "done")), ("is_locked", "=", False)]
            ).is_locked = True
