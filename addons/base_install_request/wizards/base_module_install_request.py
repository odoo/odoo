from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BaseModuleInstallRequest(models.Model):
    _name = "base.module.install.request"
    _inherit = ["mixin.mail.thread"]
    _description = "Module Activation Request"
    _rec_name = "module_id"
    _order = "create_date desc, id desc"

    module_id = fields.Many2one(
        comodel_name="ir.module.module",
        readonly=True,
        required=True,
        domain=[("state", "=", "uninstalled")],
        ondelete="cascade",
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        readonly=True,
        required=True,
    )
    user_ids = fields.Many2many(
        comodel_name="res.users",
        string="Send to:",
        compute="_compute_user_ids",
    )
    body_html = fields.Html(string="Body")

    @api.depends("module_id")
    def _compute_user_ids(self):
        users = self.env.ref("base.group_system").all_user_ids
        self.user_ids = [(6, 0, users.ids)]

    def action_send_request(self):
        self.check_singleton()
        self._send_request()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "message": _("Your request has been successfully sent"),
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _send_request(self):
        """Tell the administrators. `approval_base_install_request` replaces this
        with an approval request wherever the approval engine is installed."""
        mail_template = self.env.ref(
            "base_install_request.mail_template_base_install_request"
        )
        menu_id = self.env.ref("base.menu_apps").id
        for user in self.user_ids:
            render_ctx = dict(
                self.env.context, partner=user.partner_id, menu_id=menu_id
            )
            mail_template.with_context(render_ctx).send_mail(
                self.id,
                force_send=True,
                email_layout_xmlid="mail.mail_notification_light",
            )


class BaseModuleInstallReview(models.TransientModel):
    _name = "base.module.install.review"
    _description = "Module Activation Review"
    _rec_name = "module_id"

    module_id = fields.Many2one(
        comodel_name="ir.module.module",
        readonly=True,
        required=True,
        domain=[("state", "=", "uninstalled")],
        ondelete="cascade",
    )
    module_ids = fields.Many2many(
        comodel_name="ir.module.module",
        string="Depending Apps",
        compute="_compute_module_ids",
    )
    modules_description = fields.Html(compute="_compute_modules_description")

    @api.depends("module_id")
    def _compute_module_ids(self):
        for wizard in self:
            wizard.module_ids = wizard._get_depending_apps(wizard.module_id)

    @api.depends("module_ids")
    def _compute_modules_description(self):
        for wizard in self:
            wizard.modules_description = self.env["ir.qweb"]._render(
                "base_install_request.base_module_install_review_description",
                {"apps": wizard.module_ids},
            )

    @api.model
    def _get_depending_apps(self, module):
        if not module:
            raise UserError(_("No module selected."))
        if module.state == "installed":
            raise UserError(_("The module is already installed."))
        deps = module.upstream_dependencies()
        apps = module | deps.filtered(lambda d: d.application)
        for dep in deps:
            apps |= dep.upstream_dependencies()
        return apps

    def action_install_module(self):
        self.check_singleton()
        self.module_id.button_immediate_install()
        return {
            "type": "ir.actions.client",
            "tag": "home",
        }
