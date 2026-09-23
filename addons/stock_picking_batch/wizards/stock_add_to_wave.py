from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockAddToWave(models.TransientModel):
    _name = "stock.add.to.wave"
    _description = "Wave Transfer Lines"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get("active_model") == "stock.move.line":
            lines = self.env["stock.move.line"].browse(
                self.env.context.get("active_ids")
            )
            res["line_ids"] = self.env.context.get("active_ids")
            picking_types = lines.picking_type_id
        elif self.env.context.get("active_model") == "stock.picking":
            pickings = self.env["stock.picking"].browse(
                self.env.context.get("active_ids")
            )
            res["picking_ids"] = self.env.context.get("active_ids")
            picking_types = pickings.picking_type_id
        else:
            return res

        if len(picking_types) > 1:
            raise UserError(
                self.env._(
                    "The selected transfers should belong to the same operation type"
                )
            )
        return res

    wave_id = fields.Many2one(
        comodel_name="stock.picking.batch",
        string="Wave Transfer",
        domain="[('is_wave', '=', True), ('state', 'in', ('draft', 'in_progress'))]",
    )
    picking_ids = fields.Many2many(comodel_name="stock.picking")
    line_ids = fields.Many2many(comodel_name="stock.move.line")
    mode = fields.Selection(
        selection=[
            ("existing", "an existing wave transfer"),
            ("new", "a new wave transfer"),
        ],
        default="existing",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Responsible",
    )

    def attach_pickings(self):
        self.check_singleton()

        self = self.with_context(active_owner_id=self.user_id.id)
        wave = self.wave_id if self.mode == "existing" else self.wave_id.browse()
        _debug.pipeline(
            "add_to_wave",
            mode=self.mode,
            wave=wave,
            lines=self.line_ids,
            pickings=self.picking_ids,
            user=self.user_id,
        )
        if self.line_ids:
            company = self.line_ids.company_id
            if len(company) > 1:
                raise UserError(
                    self.env._(
                        "The selected operations should belong to a unique company."
                    )
                )
            return self.line_ids._add_to_wave(wave)
        if self.picking_ids:
            company = self.picking_ids.company_id
            if len(company) > 1:
                raise UserError(
                    self.env._(
                        "The selected transfers should belong to a unique company."
                    )
                )
        else:
            raise UserError(self.env._("Cannot create wave transfers"))

        view = self.env.ref(
            "stock_picking_batch.view_stock_move_line_list_detailed_wave"
        )
        return {
            "name": self.env._("Add Operations"),
            "type": "ir.actions.act_window",
            "view_mode": "list",
            "views": [(view.id, "list")],
            "res_model": "stock.move.line",
            "target": "new",
            "domain": [
                ("picking_id", "in", self.picking_ids.ids),
                ("state", "!=", "done"),
            ],
            "context": dict(self.env.context, active_wave_id=wave.id),
        }
