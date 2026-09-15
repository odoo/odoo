from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MrpProductionGroup(models.Model):
    _name = "mrp.production.group"
    _description = "Production Group"

    name = fields.Char(
        index="btree",
        required=True,
    )
    production_ids = fields.One2many(
        comodel_name="mrp.production",
        inverse_name="production_group_id",
        string="Productions",
    )
    move_ids = fields.One2many(
        comodel_name="stock.move",
        inverse_name="production_group_id",
        string="Stock Moves",
    )
    child_ids = fields.Many2many(
        comodel_name="mrp.production.group",
        relation="mrp_production_group_rel",
        column1="parent_group_id",
        column2="child_group_id",
        string="Child Manufacturing Orders",
    )
    parent_ids = fields.Many2many(
        comodel_name="mrp.production.group",
        relation="mrp_production_group_rel",
        column1="child_group_id",
        column2="parent_group_id",
        string="Parent Manufacturing Orders",
    )

    @api.constrains("child_ids")
    def _check_no_cyclic_dependencies(self):
        if self._has_cycle("child_ids"):
            _debug.logic("production_group_cycle", groups=self)
            raise ValidationError(_("You cannot create cyclic dependency."))
