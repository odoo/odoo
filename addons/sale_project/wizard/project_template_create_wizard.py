from odoo import api, Command, fields, models


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    partner_id = fields.Many2one("res.partner")
    allow_billable = fields.Boolean(related="template_id.allow_billable")
    role_to_users_ids = fields.One2many(compute="_compute_role_to_users_ids", readonly=False, store=True)

    @api.depends("template_id")
    def _compute_role_to_users_ids(self):
        for wizard in self:
            wizard.role_to_users_ids = (
                [Command.clear()] +
                [
                    Command.create({
                        'role_id': role.id,
                        'user_ids': [Command.clear()],
                    })
                    for role in wizard.template_id.task_ids.role_ids
                ]
                if wizard.template_id else [Command.clear()]
            )

    def _get_template_whitelist_fields(self):
        res = super()._get_template_whitelist_fields()
        if self.allow_billable:
            res.append("partner_id")
        return res

    @api.model
    def action_open_template_view(self):
        action = super().action_open_template_view()
        if self.env.context.get("from_sale_order_action"):
            context = dict(action.get("context", {}))
            context.update({
                "default_partner_id": self.env.context.get("default_partner_id"),
                "default_reinvoiced_sale_order_id": self.env.context.get("default_reinvoiced_sale_order_id"),
                "default_sale_line_id": self.env.context.get("default_sale_line_id"),
            })
            action["context"] = context
        return action

    def action_create_project_from_so(self):
        """Create a project either from template or directly if no template is set."""
        self.ensure_one()
        if self.template_id:
            project = self._create_project_from_template()
        else:
            sale_order = self.env['sale.order'].browse(self.env.context.get("default_sale_order_id"))
            so_line = sale_order.order_line[:1]
            product = so_line.product_id
            values = {
                'partner_id': sale_order.partner_id.id,
                'company_id': sale_order.company_id.id,
            }
            if len(sale_order.order_line) == 1:
                values['name'] = (
                    f"{sale_order.name} - [{product.default_code}] {product.name}"
                    if product.default_code
                    else f"{sale_order.name} - {product.name}"
                )
            else:
                values['name'] = sale_order.name
            project = self.env['project.project'].create(values)
        return project.action_view_tasks()
