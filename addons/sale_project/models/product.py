# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _selection_service_policy(self):
        service_policies = [
            # (service_policy, string)
            ('ordered_prepaid', _('Prepaid/Fixed Price')),
            ('delivered_manual', _('Based on Delivered Quantity (Manual)')),
        ]
        if self.user_has_groups('project.group_project_milestone'):
            service_policies.insert(1, ('delivered_milestones', _('Based on Milestones')))
        return service_policies

    service_tracking = fields.Selection(
        selection=[
            ('no', 'Nothing'),
            ('task_global_project', 'Task'),
            ('task_in_project', 'Project & Task'),
            ('project_only', 'Project'),
        ],
        string="Create on Order", default="no",
        help="On Sales order confirmation, this product can generate a project and/or task. \
        From those, you can track the service you are selling.\n \
        'In sale order\'s project': Will use the sale order\'s configured project if defined or fallback to \
        creating a new project based on the selected template.")
    project_id = fields.Many2one(
        'project.project', 'Project', company_dependent=True,
    )
    project_template_id = fields.Many2one(
        'project.project', 'Project Template', company_dependent=True, copy=True,
    )
    service_policy = fields.Selection('_selection_service_policy', string="Service Invoicing Policy", compute='_compute_service_policy', inverse='_inverse_service_policy')
    service_type = fields.Selection(selection_add=[
        ('milestones', 'Project Milestones'),
    ])

    @api.depends('invoice_policy', 'service_type', 'type')
    def _compute_service_policy(self):
        for product in self:
            product.service_policy = self._get_general_to_service(product.invoice_policy, product.service_type)
            if not product.service_policy and product.type == 'service':
                product.service_policy = 'ordered_prepaid'

    @api.depends('service_tracking', 'service_policy', 'type', 'sale_ok')
    def _compute_product_tooltip(self):
        super()._compute_product_tooltip()
        for record in self.filtered(lambda record: record.type == 'service' and record.sale_ok):
            if record.service_policy == 'ordered_prepaid':
                if record.service_tracking == 'no':
                    record.product_tooltip = _(
                        "Invoice ordered quantities as soon as this service is sold."
                    )
                elif record.service_tracking == 'task_global_project':
                    record.product_tooltip = _(
                        "Invoice ordered quantities as soon as this service is sold. "
                        "Create a task in an existing project to track the time spent."
                    )
                elif record.service_tracking == 'project_only':
                    record.product_tooltip = _(
                        "Invoice ordered quantities as soon as this service is sold. "
                        "Create a project for the order with a task for each sales order line "
                        "to track the time spent."
                    )
                elif record.service_tracking == 'task_in_project':
                    record.product_tooltip = _(
                        "Invoice ordered quantities as soon as this service is sold. "
                        "Create an empty project for the order to track the time spent."
                    )
            elif record.service_policy == 'delivered_milestones':
                if record.service_tracking == 'no':
                    record.product_tooltip = _(
                        "Invoice your milestones when they are reached."
                    )
                elif record.service_tracking == 'task_global_project':
                    record.product_tooltip = _(
                        "Invoice your milestones when they are reached. "
                        "Create a task in an existing project to track the time spent."
                    )
                elif record.service_tracking == 'project_only':
                    record.product_tooltip = _(
                        "Invoice your milestones when they are reached. "
                        "Create a project for the order with a task for each sales order line "
                        "to track the time spent."
                    )
                elif record.service_tracking == 'task_in_project':
                    record.product_tooltip = _(
                        "Invoice your milestones when they are reached. "
                        "Create an empty project for the order to track the time spent."
                    )
            elif record.service_policy == 'delivered_manual':
                if record.service_tracking == 'no':
                    record.product_tooltip = _(
                        "Invoice this service when it is delivered (set the quantity by hand on your sales order lines). "
                    )
                elif record.service_tracking == 'task_global_project':
                    record.product_tooltip = _(
                        "Invoice this service when it is delivered (set the quantity by hand on your sales order lines). "
                        "Create a task in an existing project to track the time spent."
                    )
                elif record.service_tracking == 'project_only':
                    record.product_tooltip = _(
                        "Invoice this service when it is delivered (set the quantity by hand on your sales order lines). "
                        "Create a project for the order with a task for each sales order line "
                        "to track the time spent."
                    )
                elif record.service_tracking == 'task_in_project':
                    record.product_tooltip = _(
                        "Invoice this service when it is delivered (set the quantity by hand on your sales order lines). "
                        "Create an empty project for the order to track the time spent."
                    )

    def _get_service_to_general_map(self):
        return {
            # service_policy: (invoice_policy, service_type)
            'ordered_prepaid': ('order', 'manual'),
            'delivered_milestones': ('delivery', 'milestones'),
            'delivered_manual': ('delivery', 'manual'),
        }

    def _get_general_to_service_map(self):
        return {v: k for k, v in self._get_service_to_general_map().items()}

    def _get_service_to_general(self, service_policy):
        return self._get_service_to_general_map().get(service_policy, (False, False))

    def _get_general_to_service(self, invoice_policy, service_type):
        general_to_service = self._get_general_to_service_map()
        return general_to_service.get((invoice_policy, service_type), False)

    @api.onchange('service_policy')
    def _inverse_service_policy(self):
        for product in self:
            if product.service_policy:
                product.invoice_policy, product.service_type = self._get_service_to_general(product.service_policy)

    @api.constrains('project_id', 'project_template_id')
    def _check_project_and_template(self):
        """ NOTE 'service_tracking' should be in decorator parameters but since ORM check constraints twice (one after setting
            stored fields, one after setting non stored field), the error is raised when company-dependent fields are not set.
            So, this constraints does cover all cases and inconsistent can still be recorded until the ORM change its behavior.
        """
        for product in self:
            if product.service_tracking == 'no' and (product.project_id or product.project_template_id):
                raise ValidationError(_('The product %s should not have a project nor a project template since it will not generate project.', product.name))
            elif product.service_tracking == 'task_global_project' and product.project_template_id:
                raise ValidationError(_('The product %s should not have a project template since it will generate a task in a global project.', product.name))
            elif product.service_tracking in ['task_in_project', 'project_only'] and product.project_id:
                raise ValidationError(_('The product %s should not have a global project since it will generate a project.', product.name))

    @api.onchange('service_tracking')
    def _onchange_service_tracking(self):
        if self.service_tracking == 'no':
            self.project_id = False
            self.project_template_id = False
        elif self.service_tracking == 'task_global_project':
            self.project_template_id = False
        elif self.service_tracking in ['task_in_project', 'project_only']:
            self.project_id = False

    @api.onchange('type')
    def _onchange_type(self):
        res = super(ProductTemplate, self)._onchange_type()
        if self.type != 'service':
            self.service_tracking = 'no'
        return res

    def write(self, vals):
        if 'type' in vals and vals['type'] != 'service':
            vals.update({
                'service_tracking': 'no',
                'project_id': False
            })
        return super(ProductTemplate, self).write(vals)


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

    def _inverse_service_policy(self):
        for product in self:
            if product.service_policy:

                product.invoice_policy, product.service_type = self.product_tmpl_id._get_service_to_general(product.service_policy)

    @api.onchange('type')
    def _onchange_type(self):
        res = super(ProductProduct, self)._onchange_type()
        if self.type != 'service':
            self.service_tracking = 'no'
        return res

    def write(self, vals):
        if 'type' in vals and vals['type'] != 'service':
            vals.update({
                'service_tracking': 'no',
                'project_id': False
            })
        return super(ProductProduct, self).write(vals)
