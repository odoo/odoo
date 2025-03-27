# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class DiscussTemplate(models.Model):
    """Templates for sending Discuss messages."""

    _name = "discuss.template"
    _inherit = ["mail.render.mixin", "template.reset.mixin"]
    _description = "Discuss Templates"
    _unrestricted_rendering = True

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "model_id" in fields and not res.get("model_id") and res.get("model"):
            res["model_id"] = self.env["ir.model"]._get(res["model"]).id
        return res

    name = fields.Char("Name", translate=True)
    model_id = fields.Many2one(
        "ir.model",
        string="Applies to",
        required=True,
        domain=[("transient", "=", False)],
        help="The type of document this template can be used with",
        ondelete="cascade",
    )
    model = fields.Char(
        "Related Model", related="model_id.model", index=True, store=True, readonly=True
    )
    subject = fields.Char(
        "Subject",
        translate=True,
        prefetch=True,
        help="Subject (placeholders may be used here)",
    )
    body = fields.Html(
        "Message",
        required=True,
        render_engine="qweb",
        render_options={"post_process": True},
        prefetch=True,
        translate=True,
        sanitize="email_outgoing",
    )

    # Overrides of mail.render.mixin
    @api.depends("model")
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        return [
            dict(vals, name=self.env._("%s (copy)", template.name))
            for template, vals in zip(self, vals_list)
        ]
