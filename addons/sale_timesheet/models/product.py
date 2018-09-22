# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_policy = fields.Selection([
        ('ordered_timesheet', 'Ordered quantities'),
        ('delivered_timesheet', 'Timesheets on tasks'),
        ('delivered_manual', 'Milestones (manually set quantities on order)')
    ], string="Invoice based on", compute='_compute_service_policy', inverse='_inverse_service_policy')
    service_type = fields.Selection(selection_add=[
        ('timesheet', 'Timesheets on project (one fare per SO/Project)'),
    ])
    service_tracking = fields.Selection([
        ('no', 'Don\'t create task'),
        ('task_global_project', 'Create a task in an existing project'),
        ('task_new_project', 'Create a task in a new project'),
        ('project_only', 'Create a new project but no task'),
    ], string="Service Tracking", default="no",
       help="On Sales order confirmation, this product can generate a project and/or task. From those, you can track the service you are selling.")
    project_id = fields.Many2one(
        'project.project', 'Project', company_dependent=True, domain=[('sale_line_id', '=', False)],
        help='Select a non billable project on which tasks can be created. This setting must be set for each company.')

    @api.depends('invoice_policy', 'service_type')
    def _compute_service_policy(self):
        for product in self:
            policy = None
            if product.invoice_policy == 'delivery':
                policy = 'delivered_manual' if product.service_type == 'manual' else 'delivered_timesheet'
            elif product.invoice_policy == 'order' and product.service_type == 'timesheet':
                policy = 'ordered_timesheet'
            product.service_policy = policy

    def _inverse_service_policy(self):
        for product in self:
            policy = product.service_policy
            if not policy and not product.invoice_policy =='delivery':
                product.invoice_policy = 'order'
                product.service_type = 'manual'
            elif policy == 'ordered_timesheet':
                product.invoice_policy = 'order'
                product.service_type = 'timesheet'
            else:
                product.invoice_policy = 'delivery'
                product.service_type = 'manual' if policy == 'delivered_manual' else 'timesheet'

    @api.onchange('service_tracking')
    def _onchange_service_tracking(self):
        if self.service_tracking != 'task_global_project':
            self.project_id = False

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'service':
            self.invoice_policy = 'order'
            self.service_type = 'timesheet'
        elif self.type == 'consu':
            if not self.invoice_policy or self.service_policy == 'ordered_timesheet':
                self.invoice_policy = 'order'
            self.service_type = 'manual'
