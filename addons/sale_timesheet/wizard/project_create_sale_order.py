# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCreateSalesOrder(models.TransientModel):
    _name = 'project.create.sale.order'
    _description = "Create a SO from project"

    @api.model
    def default_get(self, fields):
        result = super(ProjectCreateSalesOrder, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'project.project':
            raise UserError(_('You can only apply this action from a project.'))

        active_id = self._context.get('active_id')
        if 'project_id' in fields and active_id:
            result['project_id'] = active_id
            result['partner_id'] = self.env['project.project'].browse(active_id).partner_id.id
        return result

    project_id = fields.Many2one('project.project', "Project", domain=[('sale_line_id', '=', False)], help="Project to make billable", required=True)
    product_id = fields.Many2one('product.product', domain=[('type', '=', 'service'), ('invoice_policy', '=', 'delivery')], required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", domain=[('customer', '=', True)], required=True)
    price_unit = fields.Float("Price", help="Price unit of the selected product for the generated Sales Order.")
    currency_id = fields.Many2one('res.currency', string="Currency", related='product_id.currency_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price

    @api.multi
    def action_create_sale_order(self):
        # if project linked to SO line or at least on tasks with SO line, then we consider project as billable.
        if self.project_id.sale_line_id or self.project_id.tasks.mapped('sale_line_id'):
            raise UserError(_("The project is already linked to a sales order item."))

        # create SO
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'analytic_account_id': self.project_id.analytic_account_id.id,
            'client_order_ref': self.project_id.name,
        })
        sale_order.onchange_partner_id()
        sale_order.onchange_partner_shipping_id()

        planned_hours = sum(self.project_id.tasks.mapped('planned_hours'))

        # trying to simulate the SO line created a task, according to the product configuration
        # To avoid, generating a task when confirming the SO
        task_id = False
        if self.product_id.service_tracking in ['task_new_project', 'task_global_project']:
            task_id = self.env['project.task'].search([('project_id', '=', self.project_id.id)], order='create_date DESC', limit=1).id

        # create SO line
        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_id.id,
            'price_unit': self.price_unit,
            'project_id': self.project_id.id,  # prevent to re-create a project on confirmation
            'task_id': task_id,
            'product_uom_qty': sale_order.company_id.project_time_mode_id._compute_quantity(planned_hours, self.product_id.uom_id, raise_if_failure=False),
        })

        # confirm SO
        sale_order.action_confirm()

        # link project and tasks to SO line
        self.project_id.write({
            'sale_line_id': sale_order_line.id,
        })
        self.project_id.tasks.filtered(lambda t: not t.sale_line_id).write({
            'sale_line_id': sale_order_line.id,
            'partner_id': sale_order.partner_id.id,
            'email_from': sale_order.partner_id.email,
        })

        view_form_id = self.env.ref('sale.view_order_form').id
        action = self.env.ref('sale.action_orders').read()[0]
        action.update({
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': sale_order.name,
            'res_id': sale_order.id,
        })
        return action
