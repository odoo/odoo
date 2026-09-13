from odoo import Command, api, fields, models


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    bill_count = fields.Count(
        count_of="account_move_ids",
        string="Bills Count",
    )
    account_move_ids = fields.One2many(
        comodel_name="account.move",
        compute="_compute_move_ids",
    )

    # `uid`: this answers `False` outright for a user without the accounting
    # group, so the value is the acting user's. A non-stored compute's cache is
    # keyed by exactly what the field declares, and with nothing declared the
    # whole transaction shared one entry -- an accountant's read populated it
    # and the next user was served those moves. `bill_count` counts this field,
    # so the leak reached the vehicle form too.
    @api.depends_context("uid")
    def _compute_move_ids(self):
        if not self.env.user.has_group("account.group_account_readonly"):
            self.account_move_ids = False
            return

        moves = self.env["account.move.line"]._read_group(
            domain=[
                ("vehicle_id", "in", self.ids),
                ("parent_state", "!=", "cancel"),
                (
                    "move_id.move_type",
                    "in",
                    self.env["account.move"].get_purchase_types(),
                ),
            ],
            groupby=["vehicle_id"],
            aggregates=["move_id:array_agg"],
        )
        vehicle_move_mapping = {
            vehicle.id: set(move_ids) for vehicle, move_ids in moves
        }
        for vehicle in self:
            vehicle.account_move_ids = [
                Command.set(vehicle_move_mapping.get(vehicle.id, []))
            ]

    def action_view_bills(self):
        self.check_singleton()

        form_view_ref = self.env.ref("account.view_move_form", False)
        list_view_ref = self.env.ref("account_fleet.account_move_view_tree", False)

        result = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "account.action_move_in_invoice_type"
        )
        result.update(
            {
                "domain": [("id", "in", self.account_move_ids.ids)],
                "views": [(list_view_ref.id, "list"), (form_view_ref.id, "form")],
            }
        )
        return result
