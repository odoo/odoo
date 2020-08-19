# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection([
        ('no', 'Don\'t create task'),
        ('task_global_project', 'Create a task in an existing project'),
        ('task_in_project', 'Create a task in sales order\'s project'),
        ('project_only', 'Create a new project but no task')],
        string="Service Tracking", default="no",
        help="On Sales order confirmation, this product can generate a project and/or task. \
        From those, you can track the service you are selling.\n \
        'In sale order\'s project': Will use the sale order\'s configured project if defined or fallback to \
        creating a new project based on the selected template.")
    project_id = fields.Many2one(
        'project.project', 'Project', company_dependent=True,
        help='Select a billable project on which tasks can be created. This setting must be set for each company.')
    project_template_id = fields.Many2one(
        'project.project', 'Project Template', company_dependent=True, copy=True,
        help='Select a billable project to be the skeleton of the new created project when selling the current product. Its stages and tasks will be duplicated.')

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
            elif product.service_tracking in ['task_in_project', 'project_only'] and product.project_id:
                raise ValidationError(_('The product %s should not have a global project since it will generate a project.') % (product.name,))

    @api.onchange('service_tracking')
    def _onchange_service_tracking(self):
        if self.service_tracking == 'no':
            self.project_id = False
            self.project_template_id = False
        elif self.service_tracking == 'task_global_project':
            self.project_template_id = False
        elif self.service_tracking in ['task_in_project', 'project_only']:
            self.project_id = False


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.onchange('service_tracking')
    def _onchange_service_tracking(self):
        if self.service_tracking == 'no':
            self.project_id = False
            self.project_template_id = False
        elif self.service_tracking == 'task_global_project':
            self.project_template_id = False
        elif self.service_tracking in ['task_in_project', 'project_only']:
            self.project_id = False
