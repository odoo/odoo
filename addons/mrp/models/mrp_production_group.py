from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MrpProductionGroup(models.Model):
    _name = "mrp.production.group"
    _description = "Production Group"

    name = fields.Char(required=True, index="btree")
    production_ids = fields.One2many(
        "mrp.production", "production_group_id", string="Productions"
    )
    move_ids = fields.One2many(
        "stock.move", "production_group_id", string="Stock Moves"
    )
    child_ids = fields.Many2many(
        "mrp.production.group",
        "mrp_production_group_rel",
        "parent_group_id",
        "child_group_id",
        string="Child Manufacturing Orders",
    )
    parent_ids = fields.Many2many(
        "mrp.production.group",
        "mrp_production_group_rel",
        "child_group_id",
        "parent_group_id",
        string="Parent Manufacturing Orders",
    )

    @api.constrains("child_ids")
    def _check_no_cyclic_dependencies(self):
        if self._has_cycle("child_ids"):
            raise ValidationError(_("You cannot create cyclic dependency."))
