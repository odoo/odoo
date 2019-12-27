# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectTaskCreateSalesOrder(models.TransientModel):
    _name = 'project.task.create.sale.order'
    _description = "Create SO from task"

    @api.model
    def default_get(self, fields):
        result = super(ProjectTaskCreateSalesOrder, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'project.task':
            raise UserError(_("You can only apply this action from a task."))

        active_id = self._context.get('active_id')
        if 'task_id' in fields and active_id:
            task = self.env['project.task'].browse(active_id)
            if task.billable_type != 'no':
                raise UserError(_("The task is already billable."))
            result['task_id'] = active_id
            result['partner_id'] = task.partner_id.id
        return result

    task_id = fields.Many2one('project.task', "Task", domain=[('sale_line_id', '=', False)], help="Task for which we are creating a sales order", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", required=True, help="Customer of the sales order")
    product_id = fields.Many2one('product.product', domain=[('type', '=', 'service'), ('invoice_policy', '=', 'delivery'), ('service_type', '=', 'timesheet')], string="Service", help="Product of the sales order item. Must be a service invoiced based on timesheets on tasks. The existing timesheet will be linked to this product.", required=True, ondelete='cascade')
    price_unit = fields.Float("Unit Price", help="Unit price of the sales order item.")
    currency_id = fields.Many2one('res.currency', string="Currency", related='product_id.currency_id', readonly=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
        else:
            self.price_unit = 0.0

    def action_create_sale_order(self):
        sale_order = self._prepare_sale_order()
        sale_order.action_confirm()
        view_form_id = self.env.ref('sale.view_order_form').id
        action = self.env.ref('sale.action_orders').read()[0]
        action.update({
            'views': [(view_form_id, 'form')],
            'view_mode': 'form',
            'name': sale_order.name,
            'res_id': sale_order.id,
        })
        return action

    def _prepare_sale_order(self):
        # if task linked to SO line, then we consider it as billable.
        if self.task_id.sale_line_id:
            raise UserError(_("The task is already linked to a sales order item."))

        timesheet_with_so_line = self.env['account.analytic.line'].search_count([('task_id', '=', self.task_id.id), ('so_line', '!=', False), ('project_id', '!=', False)])
        if timesheet_with_so_line:
            raise UserError(_('The sales order cannot be created because some timesheets of this task are already linked to another sales order.'))

        # create SO
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'analytic_account_id': self.task_id.project_id.analytic_account_id.id,
        })
        sale_order.onchange_partner_id()
        sale_order.onchange_partner_shipping_id()

        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': self.product_id.id,
            'price_unit': self.price_unit,
            'project_id': self.task_id.project_id.id,  # prevent to re-create a project on confirmation
            'task_id': self.task_id.id,
            'product_uom_qty': self.task_id.total_hours_spent,
        })

        # link task to SOL
        self.task_id.write({
            'sale_line_id': sale_order_line.id,
            'partner_id': sale_order.partner_id.id,
            'email_from': sale_order.partner_id.email,
        })

        # assign SOL to timesheets
        self.env['account.analytic.line'].search([('task_id', '=', self.task_id.id), ('so_line', '=', False)]).write({
            'so_line': sale_order_line.id
        })

        return sale_order
