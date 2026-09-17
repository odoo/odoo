from typing import Self

from odoo import api, fields, models
from odoo.api import ValuesType


class IrUiViewCustom(models.Model):
    _name = "ir.ui.view.custom"
    _description = "Custom View"
    _order = "create_date desc, id desc"
    _rec_name = "user_id"
    _allow_sudo_commands = False

    ref_id = fields.Many2one(
        comodel_name="ir.ui.view",
        string="Original View",
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        required=True,
        ondelete="cascade",
    )
    arch = fields.Text(
        string="View Architecture",
        required=True,
    )

    _user_id_ref_id = models.Index("(user_id, ref_id)")

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        records = super().create(vals_list)
        self.env["ir.ui.view"]._forget_customized_views()
        return records
