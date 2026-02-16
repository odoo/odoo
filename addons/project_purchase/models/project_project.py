from odoo import fields, models, _


class ProjectProject(models.Model):
    _inherit = "project.project"

    purchase_orders_count = fields.Integer('# Purchase Orders', compute='_compute_purchase_orders_count', groups='purchase.group_purchase_user', export_string_translation=False)

    def _compute_purchase_orders_count(self):
        purchase_orders_per_project = dict(
            self.env['purchase.order']._read_group(
                domain=[
                    ('project_id', 'in', self.ids),
                    ('order_line', '!=', False),
                ],
                groupby=['project_id'],
                aggregates=['id:array_agg'],
            )
        )
        purchase_orders_count_per_project_from_lines = dict(
            self.env['purchase.order.line']._read_group(
                domain=[
                    ('order_id', 'not in', [order_id for values in purchase_orders_per_project.values() for order_id in values]),
                    ('analytic_distribution', 'in', self.account_id.ids),
                ],
                groupby=['analytic_distribution'],
                aggregates=['__count'],
            )
        )

        projects_no_account = self.filtered(lambda project: not project.account_id)
        for project in projects_no_account:
            project.purchase_orders_count = len(purchase_orders_per_project.get(project, []))

        purchase_orders_per_project = {project.account_id.id: len(orders) for project, orders in purchase_orders_per_project.items()}
        for project in (self - projects_no_account):
            project.purchase_orders_count = purchase_orders_per_project.get(project.account_id.id, 0) + purchase_orders_count_per_project_from_lines.get(project.account_id.id, 0)

    # ----------------------------
    #  Actions
    # ----------------------------

    def action_open_project_purchase_orders(self):
        purchase_orders = self.env['purchase.order.line'].search([
            '|',
                ('analytic_distribution', 'in', self.account_id.ids),
                ('order_id.project_id', '=', self.id),
        ]).order_id
        action_window = {
            'name': self.env._('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [
                [False, 'list'], [self.env.ref('purchase.purchase_order_view_kanban_without_dashboard').id, 'kanban'],
                [False, 'form'], [False, 'calendar'], [False, 'pivot'], [False, 'graph'], [False, 'activity'],
            ],
            'domain': [('id', 'in', purchase_orders.ids)],
            'context': {
                'default_project_id': self.id,
            },
            'help': "<p class='o_view_nocontent_smiling_face'>%s</p><p>%s</p>" % (
                _("No purchase order found. Let's create one."),
                _("Once you ordered your products from your supplier, confirm your request for quotation and it will turn "
                    "into a purchase order."),
            ),
        }
        if len(purchase_orders) == 1 and not self.env.context.get('from_embedded_action'):
            action_window['views'] = [[False, 'form']]
            action_window['res_id'] = purchase_orders.id
        return action_window
