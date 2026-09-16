from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class TagTag(models.Model):
    _name = "tag.tag"
    _inherit = ["mixin.tag.nested"]
    _description = "Tag"

    parent_id = fields.Many2one(
        comodel_name="tag.tag",
        string="Parent Tag",
        index=True,
        ondelete="cascade",
    )
    child_ids = fields.One2many(
        comodel_name="tag.tag",
        inverse_name="parent_id",
        string="Child Tags",
    )

    @api.model_create_multi
    def create(self, vals_list):
        _debug.lifecycle(
            "create",
            count=len(vals_list),
            nested=sum(1 for vals in vals_list if vals.get("parent_id")),
        )
        return super().create(vals_list)

    def write(self, vals):
        _debug.lifecycle("write", count=len(self), fields=list(vals))
        return super().write(vals)

    def unlink(self):
        _debug.lifecycle("unlink", count=len(self))
        return super().unlink()
