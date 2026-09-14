from odoo import Command, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = "project.template.create.wizard"

    partner_id = fields.Many2one(comodel_name="res.partner")
    allow_billable = fields.Boolean(related="template_id.allow_billable")
    role_to_users_ids = fields.One2many(
        compute="_compute_role_to_users_ids",
        store=True,
        readonly=False,
    )

    @api.depends("template_id")
    def _compute_role_to_users_ids(self):
        for wizard in self:
            wizard.role_to_users_ids = (
                [Command.clear()]
                + [
                    Command.create(
                        {
                            "role_id": role.id,
                            "user_ids": [Command.clear()],
                        }
                    )
                    for role in wizard.template_id.task_ids.role_ids
                ]
                if wizard.template_id
                else [Command.clear()]
            )

    def _get_fields_template_whitelist(self):
        res = super()._get_fields_template_whitelist()
        if self.allow_billable:
            res.append("partner_id")
        return res

    @api.model
    def action_view_template_view(self):
        action = super().action_view_template_view()
        if self.env.context.get("from_sale_order_action"):
            context = dict(action.get("context", {}))
            context.update(
                {
                    "default_partner_id": self.env.context.get("default_partner_id"),
                    "default_reinvoiced_sale_order_id": self.env.context.get(
                        "default_reinvoiced_sale_order_id"
                    ),
                    "default_sale_line_id": self.env.context.get(
                        "default_sale_line_id"
                    ),
                }
            )
            action["context"] = context
        return action

    def action_create_project_from_so(self):
        self.check_singleton()
        _debug.logic(
            "project_from_so",
            wizard=self,
            by="template" if self.template_id else "blank",
            template=self.template_id,
        )
        if self.template_id:
            project = self._create_project_from_template()
        else:
            sale_order = self.env["sale.order"].browse(
                self.env.context.get("default_sale_order_id")
            )
            so_line = sale_order.line_ids[:1]
            product = so_line.product_id
            values = {
                "partner_id": sale_order.partner_id.id,
                "company_id": sale_order.company_id.id,
            }
            if len(sale_order.line_ids) == 1:
                values["name"] = (
                    f"{sale_order.name} - [{product.default_code}] {product.name}"
                    if product.default_code
                    else f"{sale_order.name} - {product.name}"
                )
            else:
                values["name"] = sale_order.name
            project = self.env["project.project"].create(values)
        _debug.lifecycle("project_created_from_so_wizard", wizard=self, project=project)
        return project.action_view_tasks()
