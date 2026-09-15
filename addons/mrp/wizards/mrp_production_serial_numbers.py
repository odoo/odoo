from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpProductionSerials(models.TransientModel):
    _name = "mrp.production.serials"
    _description = "Assign serial numbers to production order"

    production_id = fields.Many2one(comodel_name="mrp.production")

    workorder_id = fields.Many2one(comodel_name="mrp.workorder")

    lot_name = fields.Char(
        string="First SN",
        compute="_compute_serial_defaults",
        store=True,
        readonly=False,
    )
    lot_quantity = fields.Integer(
        string="Number of SN",
        compute="_compute_lot_quantity",
        store=True,
        readonly=False,
    )

    serial_numbers = fields.Text(
        string="Produced Serial Numbers",
        compute="_compute_serial_defaults",
        store=True,
        readonly=False,
    )

    @api.depends("production_id")
    def _compute_serial_defaults(self):
        for wizard in self:
            wizard.serial_numbers = "\n".join(
                wizard.production_id.lot_producing_ids.mapped("name")
            )
            if wizard.lot_name:
                continue
            wizard.lot_name = wizard.production_id.lot_producing_ids[:1].name
            if not wizard.lot_name:
                wizard.lot_name = wizard.production_id.product_id.next_serial

    @api.depends("production_id")
    def _compute_lot_quantity(self):
        for wizard in self:
            wizard.lot_quantity = round(wizard.production_id.product_qty)

    def _get_names_from_serial_numbers(self):
        self.check_singleton()
        return list(
            dict.fromkeys(
                name for name in (self.serial_numbers or "").split("\n") if name.strip()
            )
        )

    @api.onchange("serial_numbers")
    def _onchange_serial_numbers(self):
        self.serial_numbers = "\n".join(self._get_names_from_serial_numbers())

    def action_generate_serial_numbers(self):
        self.check_singleton()
        if self.lot_name and self.lot_quantity:
            lots = self.env["stock.lot"].prepare_lot_names(
                self.lot_name, self.lot_quantity
            )
            self.serial_numbers = "\n".join(lots)
            self._onchange_serial_numbers()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "mrp.action_assign_serial_numbers"
        )
        action["res_id"] = self.id
        return action

    def action_split_and_assign_serials(self):
        self.check_singleton()
        lots = self._get_or_create_lots()

        _debug.pipeline(
            "serials_split", production=self.production_id.id, lots=len(lots)
        )
        split_amounts = {self.production_id: [1] * len(lots)}
        mos = self.production_id._split_productions(amounts=split_amounts)
        for mo, serial in zip(mos[: len(lots)], lots, strict=True):
            mo.lot_producing_ids = [Command.link(serial.id)]
        return self._prepare_action_closing(mos)

    def action_apply(self):
        self.check_singleton()
        lots = self._get_or_create_lots()
        _debug.lifecycle("serials_applied", production=self.production_id.id, lots=lots)
        self.production_id.lot_producing_ids = lots
        if self.production_id.qty_producing != len(
            self.production_id.lot_producing_ids
        ):
            self.production_id.qty_producing = len(self.production_id.lot_producing_ids)
        (self.workorder_id or self.production_id).set_qty_producing()
        return self._prepare_action_closing()

    def _prepare_action_closing(self, mos=False):
        mos = mos or self.production_id
        print_actions = mos._prepare_actions_autoprint_generated_lots()
        if print_actions:
            return {
                "type": "ir.actions.client",
                "tag": "do_multi_print",
                "context": {},
                "params": {
                    "reports": print_actions,
                },
            }
        return {"type": "ir.actions.act_window_close"}

    def _get_or_create_lots(self):
        self.check_singleton()
        if not self.serial_numbers:
            _debug.logic("serials_refused", reason="none_entered", wizard=self.id)
            raise UserError(self.env._("There is no serial numbers to apply."))
        lots = self._get_names_from_serial_numbers()
        if not lots:
            _debug.logic("serials_refused", reason="none_valid", wizard=self.id)
            raise UserError(self.env._("No valid serial numbers provided."))
        existing_lots = (
            self.env["stock.lot"]
            .with_context(active_test=False)
            .search(
                [
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.production_id.company_id.id),
                    ("product_id", "=", self.production_id.product_id.id),
                    ("name", "in", lots),
                ]
            )
        )
        existing_lots.filtered(lambda lot: not lot.active).action_unarchive()
        existing_lot_names = existing_lots.mapped("name")
        new_lots_vals = []
        sequence = self.production_id.product_id.lot_sequence_id
        for lot_name in sorted(lots):
            if lot_name in existing_lot_names:
                continue
            if sequence and lot_name == sequence.get_next_char(
                sequence.number_next_actual
            ):
                sequence.sudo().number_next_actual += 1
            new_lots_vals.append(
                {
                    "name": lot_name,
                    "product_id": self.production_id.product_id.id,
                }
            )
        new_lots = self.env["stock.lot"].create(new_lots_vals)
        _debug.lifecycle(
            "serial_lots_resolved",
            production=self.production_id.id,
            wanted=len(lots),
            existing=len(existing_lots),
            created=len(new_lots),
        )
        return existing_lots + new_lots
