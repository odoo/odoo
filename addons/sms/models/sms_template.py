from odoo import _, api, fields, models


class SmsTemplate(models.Model):
    "Templates for sending SMS"

    _name = "sms.template"
    _inherit = ["mixin.mail.render", "mixin.template.reset"]
    _description = "SMS Templates"

    _unrestricted_rendering = True
    # Declared, not inferred: the type-based guess also named `model` (a
    # related model name), `template_fs` (a filesystem path) and `name`,
    # none of which any engine renders.
    _dynamic_field_names = frozenset({"body", "lang"})

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if "model_id" in fields and not res.get("model_id") and res.get("model"):
            res["model_id"] = self.env["ir.model"]._get(res["model"]).id
        return res

    name = fields.Char(translate=True)
    model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Applies to",
        required=True,
        domain=["&", ("is_mail_thread_sms", "=", True), ("transient", "=", False)],
        ondelete="cascade",
        help="The type of document this template can be used with",
    )
    model = fields.Char(
        related="model_id.model",
        string="Related Document Model",
        readonly=True,
    )
    body = fields.Char(
        translate=True,
        required=True,
    )
    # Use to create contextual action (same as for email template)
    sidebar_action_id = fields.Many2one(
        comodel_name="ir.actions.act_window",
        string="Sidebar action",
        copy=False,
        readonly=True,
        help="Sidebar action to make this template available on records "
        "of the related document model",
    )

    # Overrides of mixin.mail.render
    @api.depends("model")
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.model

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    def copy_data(self, default=None):
        vals_list = super().copy_data(default=default)
        # copy_data returns one vals dict per record (ORM contract), so self and vals_list align
        return [
            dict(vals, name=self.env._("%s (copy)", template.name))
            for template, vals in zip(self, vals_list, strict=True)
        ]

    def copy_translations(self, new, excluded=()):
        # ``copy_data`` renames ``name`` in the duplicating user's language
        # only; without this the copy would keep the source record's exact
        # ``name`` in every other language.
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    def unlink(self):
        self.sudo().mapped("sidebar_action_id").unlink()
        return super().unlink()

    def action_create_sidebar_action(self):
        ActWindow = self.env["ir.actions.act_window"]
        view = self.env.ref("sms.sms_composer_view_form")

        for template in self:
            button_name = _("Send SMS (%s)", template.name)
            action = ActWindow.create(
                {
                    "name": button_name,
                    "type": "ir.actions.act_window",
                    "res_model": "sms.composer",
                    # Set sms_composition_mode to 'guess' so the composer picks mass or comment mode
                    "context": "{'default_template_id' : %d, 'sms_composition_mode': 'guess', 'default_res_ids': active_ids, 'default_res_id': active_id}"
                    % (template.id),
                    "view_mode": "form",
                    "view_id": view.id,
                    "target": "new",
                    "binding_model_id": template.model_id.id,
                }
            )
            template.write({"sidebar_action_id": action.id})
        return True

    def action_unlink_sidebar_action(self):
        for template in self:
            if template.sidebar_action_id:
                template.sidebar_action_id.unlink()
        return True
