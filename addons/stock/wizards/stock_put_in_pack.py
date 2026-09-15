from odoo import api, fields, models

from ..tools import debug_log as dbg


class StockPutInPack(models.TransientModel):
    _name = "stock.put.in.pack"
    _description = "Put In Pack Wizard"

    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination",
    )
    move_line_ids = fields.Many2many(
        comodel_name="stock.move.line",
        string="Move lines",
    )
    package_ids = fields.Many2many(
        comodel_name="stock.package",
        string="Packages",
    )
    package_type_id = fields.Many2one(comodel_name="stock.package.type")
    package_type_sequence_id = fields.Many2one(related="package_type_id.sequence_id")
    result_package_id = fields.Many2one(
        comodel_name="stock.package",
        string="Package",
    )
    origin_package_ids = fields.Many2many(
        comodel_name="stock.package",
        compute="_compute_origin_package_ids",
    )

    @api.depends("move_line_ids", "package_ids", "result_package_id")
    def _compute_origin_package_ids(self):
        for wizard in self:
            packages = wizard.package_ids
            if wizard.move_line_ids:
                packages |= wizard.move_line_ids.result_package_id
            wizard.origin_package_ids = packages.parent_package_id

    @api.onchange("package_type_id")
    def _onchange_package_type_id(self):
        if (
            self.package_type_id
            and self.result_package_id
            and self.result_package_id.package_type_id != self.package_type_id
        ):
            self.result_package_id = False

    def action_put_in_pack(self):
        context = self._prepare_put_in_pack_context()
        dbg.pipeline.debug(
            "put in pack wizard: packages %s lines %s -> package %s type %s",
            dbg.rec(self.package_ids),
            dbg.rec(self.move_line_ids),
            self.result_package_id.id,
            self.package_type_id.id,
        )
        if self.package_ids:
            return self.package_ids.with_context(**context).action_put_in_pack(
                package_id=self.result_package_id.id,
                package_type_id=self.package_type_id.id,
            )
        return self.move_line_ids.with_context(**context).action_put_in_pack(
            package_id=self.result_package_id.id,
            package_type_id=self.package_type_id.id,
        )

    def _prepare_put_in_pack_context(self):
        return {
            **self.env.context,
            "from_package_wizard": True,
        }
