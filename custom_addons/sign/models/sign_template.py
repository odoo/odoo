from odoo import api, fields, models


class SignTemplate(models.Model):
    _name = "sign.template"
    _description = "Sign Template"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(required=True, tracking=True)
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Document",
        ondelete="set null",
    )
    sign_item_ids = fields.One2many(
        comodel_name="sign.item",
        inverse_name="template_id",
        string="Sign Items",
        copy=True,
    )
    active = fields.Boolean(default=True)
    favorited_ids = fields.Many2many(
        comodel_name="res.users",
        relation="sign_template_favorite_user_rel",
        column1="template_id",
        column2="user_id",
        string="Favorite Users",
    )
    color = fields.Integer()
    signed_count = fields.Integer(
        compute="_compute_signed_count",
        string="Signed Count",
    )
    request_ids = fields.One2many(
        comodel_name="sign.request",
        inverse_name="template_id",
        string="Requests",
    )

    @api.depends("request_ids.state")
    def _compute_signed_count(self):
        counts = {}
        grouped = self.env["sign.request"].read_group(
            [("template_id", "in", self.ids), ("state", "=", "signed")],
            ["template_id"],
            ["template_id"],
        )
        for row in grouped:
            template = row.get("template_id")
            if template:
                counts[template[0]] = row.get("template_id_count", row.get("__count", 0))
        for template in self:
            template.signed_count = counts.get(template.id, 0)
