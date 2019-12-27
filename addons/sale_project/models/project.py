# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Project(models.Model):
    _inherit = 'project.project'

    sale_line_id = fields.Many2one(
        'sale.order.line', 'Sales Order Item', copy=False,
        domain="[('is_expense', '=', False), ('order_id', '=', sale_order_id), ('state', 'in', ['sale', 'done']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Sales order item to which the project is linked. If an employee timesheets on a task that does not have a "
        "sale order item defines, and if this employee is not in the 'Employee/Sales Order Item Mapping' of the project, "
        "the timesheet entry will be linked to the sales order item defined on the project.")
    sale_order_id = fields.Many2one('sale.order', 'Sales Order', domain="[('partner_id', '=', partner_id)]", readonly=True, copy=False, help="Sales order to which the project is linked.")

    _sql_constraints = [
        ('sale_order_required_if_sale_line', "CHECK((sale_line_id IS NOT NULL AND sale_order_id IS NOT NULL) OR (sale_line_id IS NULL))", 'The Project should be linked to a Sale Order to select an Sale Order Items.'),
    ]

    @api.model
    def _map_tasks_default_valeus(self, task, project):
        defaults = super()._map_tasks_default_valeus(task, project)
        defaults['sale_line_id'] = False
        return defaults


class ProjectTask(models.Model):
    _inherit = "project.task"

    sale_order_id = fields.Many2one('sale.order', 'Sales Order', help="Sales order to which the task is linked.")
    sale_line_id = fields.Many2one(
        'sale.order.line', 'Sales Order Item', domain="[('is_service', '=', True), ('order_partner_id', 'child_of', commercial_partner_id), ('is_expense', '=', False), ('state', 'in', ['sale', 'done']), ('order_id', '=?', project_sale_order_id)]",
        compute='_compute_sale_line', store=True, readonly=False, copy=False,
        help="Sales order item to which the task is linked. If an employee timesheets on a this task, "
        "and if this employee is not in the 'Employee/Sales Order Item Mapping' of the project, the "
        "timesheet entry will be linked to this sales order item.")
    project_sale_order_id = fields.Many2one('sale.order', string="project's sale order", related='project_id.sale_order_id')

    @api.depends('project_id.sale_line_id.order_partner_id')
    def _compute_partner_id(self):
        for task in self:
            if not task.partner_id:
                task.partner_id = task.project_id.sale_line_id.order_partner_id
        super()._compute_partner_id()

    @api.depends('partner_id.commercial_partner_id', 'sale_line_id.order_partner_id.commercial_partner_id', 'parent_id.sale_line_id', 'project_id.sale_line_id')
    def _compute_sale_line(self):
        for task in self:
            if not task.sale_line_id:
                task.sale_line_id = task.parent_id.sale_line_id or task.project_id.sale_line_id
            # check sale_line_id and customer are coherent
            if task.sale_line_id.order_partner_id.commercial_partner_id != task.partner_id.commercial_partner_id:
                task.sale_line_id = False

    @api.constrains('sale_line_id')
    def _check_sale_line_type(self):
        for task in self.sudo():
            if task.sale_line_id:
                if not task.sale_line_id.is_service or task.sale_line_id.is_expense:
                    raise ValidationError(_('You cannot link the order item %s - %s to this task because it is a re-invoiced expense.' % (task.sale_line_id.order_id.id, task.sale_line_id.product_id.name)))

    def unlink(self):
        if any(task.sale_line_id for task in self):
            raise ValidationError(_('You have to unlink the task from the sale order item in order to delete it.'))
        return super().unlink()

    # ---------------------------------------------------
    # Actions
    # ---------------------------------------------------

    def action_view_so(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "views": [[False, "form"]],
            "res_id": self.sale_order_id.id,
            "context": {"create": False, "show_sale": True},
        }

    def rating_get_partner_id(self):
        partner = self.partner_id or self.sale_line_id.order_id.partner_id
        if partner:
            return partner
        return super().rating_get_partner_id()
