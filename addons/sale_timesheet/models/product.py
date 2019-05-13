# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_policy = fields.Selection([
        ('ordered_timesheet', 'Ordered quantities'),
        ('delivered_timesheet', 'Timesheets on tasks'),
        ('delivered_manual', 'Milestones (manually set quantities on order)')
    ], string="Service Invoicing Policy", compute='_compute_service_policy', inverse='_inverse_service_policy')
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
        'project.project', 'Project', company_dependent=True, domain=[('billable_type', '=', 'no')],
        help='Select a non billable project on which tasks can be created. This setting must be set for each company.')
    project_template_id = fields.Many2one(
        'project.project', 'Project Template', company_dependent=True, domain=[('billable_type', '=', 'no')], copy=True,
        help='Select a non billable project to be the skeleton of the new created project when selling the current product. Its stages and tasks will be duplicated.')

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

    @api.constrains('project_id', 'project_template_id')
    def _check_project_and_template(self):
        """ NOTE 'service_tracking' should be in decorator parameters but since ORM check constraints twice (one after setting
            stored fields, one after setting non stored field), the error is raised when company-dependent fields are not set.
            So, this constraints does cover all cases and inconsistent can still be recorded until the ORM change its behavior.
        """
        for product in self:
            if product.service_tracking == 'no' and (product.project_id or product.project_template_id):
                raise ValidationError(_('The product %s should not have a project nor a project template since it will not generate project.') % (product.name,))
            elif product.service_tracking == 'task_global_project' and product.project_template_id:
                raise ValidationError(_('The product %s should not have a project template since it will generate a task in a global project.') % (product.name,))
            elif product.service_tracking in ['task_new_project', 'project_only'] and product.project_id:
                raise ValidationError(_('The product %s should not have a global project since it will generate a project.') % (product.name,))

    @api.onchange('service_tracking')
    def _onchange_service_tracking(self):
        if self.service_tracking == 'no':
            self.project_id = False
            self.project_template_id = False
        elif self.service_tracking == 'task_global_project':
            self.project_template_id = False
        elif self.service_tracking in ['task_new_project', 'project_only']:
            self.project_id = False

    @api.onchange('type')
    def _onchange_type(self):
        super(ProductTemplate, self)._onchange_type()
        if self.type == 'service' and not self.invoice_policy:
            self.invoice_policy = 'order'
            self.service_type = 'timesheet'
        elif self.type == 'consu' and not self.invoice_policy and self.service_policy == 'ordered_timesheet':
            self.invoice_policy = 'order'


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('service_tracking')
    def _onchange_service_tracking(self):
        if self.service_tracking == 'no':
            self.project_id = False
            self.project_template_id = False
        elif self.service_tracking == 'task_global_project':
            self.project_template_id = False
        elif self.service_tracking in ['task_new_project', 'project_only']:
            self.project_id = False
