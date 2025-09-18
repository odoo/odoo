from odoo import fields, models


class IrUiViewCustom(models.Model):
    _name = "ir.ui.view.custom"
    _description = "Custom View"
    _order = "create_date desc, id desc"  # search(limit=1) should return the last customization
    _rec_name = "user_id"
    _allow_sudo_commands = False

    ref_id = fields.Many2one(
        "ir.ui.view",
        string="Original View",
        index=True,
        required=True,
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        "res.users",
        string="User",
        index=True,
        required=True,
        ondelete="cascade",
    )
    arch = fields.Text(string="View Architecture", required=True)

    _user_id_ref_id = models.Index("(user_id, ref_id)")
