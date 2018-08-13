# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp


class ProjectCreateSalesOrder(models.TransientModel):
    _name = 'project.create.sale.order'
    _description = "Create a SO from project"

    @api.model
    def default_get(self, fields):
        result = super(ProjectCreateSalesOrder, self).default_get(fields)

        active_model = self._context.get('active_model')
        if active_model != 'project.project':
            raise UserError(_("You can only apply this action from a project."))

        active_id = self._context.get('active_id')
        if 'project_id' in fields and active_id:
            project = self.env['project.project'].browse(active_id)
            if project.billable_type != 'no':
                raise UserError(_("The project is already billable."))
            result['project_id'] = active_id
            result['partner_id'] = project.partner_id.id
        return result

    project_id = fields.Many2one('project.project', "Project", domain=[('sale_line_id', '=', False)], help="Project to make billable", required=True)
    partner_id = fields.Many2one('res.partner', string="Customer", domain=[('customer', '=', True)], required=True)
    line_ids = fields.One2many('project.create.sale.order.line', 'wizard_id', string='Lines')

    @api.multi
    def action_create_sale_order(self):
        # if project linked to SO line or at least on tasks with SO line, then we consider project as billable.
        if self.project_id.sale_line_id:
            raise UserError(_("The project is already linked to a sales order item."))

        if not self.line_ids:
            raise UserError(_("At least one Sale Order Items should be filled."))

        # create SO
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'analytic_account_id': self.project_id.analytic_account_id.id,
            'client_order_ref': self.project_id.name,
        })
        sale_order.onchange_partner_id()
        sale_order.onchange_partner_shipping_id()

        # trying to simulate the SO line created a task, according to the product configuration
        # To avoid, generating a task when confirming the SO
        task_id = self.env['project.task'].search([('project_id', '=', self.project_id.id)], order='create_date DESC', limit=1).id
        project_id = self.project_id.id

        # create SO lines
        for wizard_line in self.line_ids:
            values = {
                'order_id': sale_order.id,
                'product_id': wizard_line.product_id.id,
                'price_unit': wizard_line.price_unit,
                'product_uom_qty': wizard_line.quantity,
            }
            if wizard_line.product_id.service_tracking in ['task_new_project', 'task_global_project']:
                values['task_id'] = task_id
            if wizard_line.product_id.service_tracking in ['task_new_project', 'project_only']:
                values['project_id'] = project_id

            sale_order_line = self.env['sale.order.line'].create(values)

        # confirm SO
        sale_order.action_confirm()

        # link project and tasks to SO line according to billable type
        if len(self.line_ids) == 1:
            self.project_id.write({
                'sale_order_id': sale_order.id,
                'sale_line_id': sale_order_line.id,
                'partner_id': self.partner_id.id,
            })
            self.project_id.tasks.filtered(lambda task: task.billable_type == 'no').write({
                'sale_line_id': sale_order_line.id,
                'partner_id': sale_order.partner_id.id,
                'email_from': sale_order.partner_id.email,
            })
        else:
            self.project_id.write({
                'sale_order_id': sale_order.id,
                'partner_id': self.partner_id.id,
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


class ProjectCreateSalesOrderLine(models.TransientModel):
    _name = 'project.create.sale.order.line'
    _order = 'id,create_date'

    wizard_id = fields.Many2one('project.create.sale.order', required=True)
    product_id = fields.Many2one('product.product', domain=[('type', '=', 'service')], string="Service", required=True)
    price_unit = fields.Float("Price", default=1.0)
    quantity = fields.Float("Quantity", digits=dp.get_precision('Product Unit of Measure'), required=True, default=1.0)
    currency_id = fields.Many2one('res.currency', string="Currency", related='product_id.currency_id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.lst_price
