from odoo import api, Command, fields, models
from odoo.tools import OrderedSet


class ProjectTemplateCreateWizard(models.TransientModel):
    _inherit = 'project.template.create.wizard'

    partner_id = fields.Many2one("res.partner")
    allow_billable = fields.Boolean(related="template_id.allow_billable")
    role_to_users_ids = fields.One2many(compute="_compute_role_to_users_ids", readonly=False, store=True)
    sale_warning_text = fields.Text('Project Template Warning', compute='_compute_sale_warning_text', help='Warning for the partner as set by the user.')

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

    @api.depends('partner_id.name', 'partner_id.sale_warn_msg')
    def _compute_sale_warning_text(self):
        if not self.env.user.has_group("sale.group_warning_sale"):
            self.sale_warning_text = ""
            return
        for project in self:
            warnings = OrderedSet()
            if partner_msg := project.partner_id.sale_warn_msg:
                warnings.add(
                    (project.partner_id.name or project.partner_id.display_name) + " - " + partner_msg
                )
            if partner_parent_msg := project.partner_id.parent_id.sale_warn_msg:
                parent = project.partner_id.parent_id
                warnings.add((parent.name or parent.display_name) + " - " + partner_parent_msg)
            project.sale_warning_text = "\n".join(warnings)

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
        so_name = self.env.context.get('default_name')
        if self.template_id:
            self.name = "%s - %s" % (so_name, self.template_id.name)
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
                sale_line_name_parts = so_line.name.split('\n')
                if sale_line_name_parts and sale_line_name_parts[0] == product.display_name:
                    sale_line_name_parts.pop(0)
                if len(sale_line_name_parts) == 1 and sale_line_name_parts[0]:
                    name = sale_line_name_parts[0]
                else:
                    name = "[%s] %s" % (product.default_code, product.name) if product.default_code else product.name
                    values['description'] = '<br/>'.join(sale_line_name_parts)
                values['name'] = "%s - %s" % (so_name, product.project_template_id.name or name)
            else:
                values['name'] = so_name
            project = self.env['project.project'].create(values)
        return project.action_view_tasks()
