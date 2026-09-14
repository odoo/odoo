from odoo import fields, models

from ..tools import debug_log as dbg


class StockPackageHistory(models.Model):
    _name = "stock.package.history"
    _description = "Stock Package History"
    _check_company_auto = True

    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
        required=True,
    )
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Origin Location",
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination Location",
    )
    move_line_ids = fields.One2many(
        comodel_name="stock.move.line",
        inverse_name="package_history_id",
        string="Move Lines",
        required=True,
    )
    package_id = fields.Many2one(
        comodel_name="stock.package",
        required=True,
        ondelete="cascade",
    )
    package_name = fields.Char(required=True)
    package_type_id = fields.Many2one(
        comodel_name="stock.package.type",
        related="package_id.package_type_id",
    )
    parent_orig_id = fields.Many2one(
        comodel_name="stock.package",
        string="Origin Container",
    )
    parent_orig_name = fields.Char(string="Origin Container Name")
    parent_dest_id = fields.Many2one(
        comodel_name="stock.package",
        string="Destination Container",
    )
    parent_dest_name = fields.Char(string="Destination Container Name")
    outermost_dest_id = fields.Many2one(
        comodel_name="stock.package",
        string="Outermost Destination Container",
    )
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Transfers",
    )

    def action_view_package(self):
        self.check_singleton()
        dbg.lifecycle.debug(
            "[package_history:%s] action_view_package -> package %s",
            self.id,
            self.package_id.id,
        )
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "stock.package",
            "res_id": self.package_id.id,
        }

    def _get_complete_dest_name_except_outermost(self):
        self.check_singleton()
        if not self.parent_dest_id:
            dbg.logic.debug(
                "[package_history:%s] no destination container, complete name is empty",
                self.id,
            )
            return ""
        name = " > ".join(self.package_name.split(" > ")[1:])
        dbg.logic.debug(
            "[package_history:%s] complete dest name below outermost: %s",
            self.id,
            name,
        )
        return name
