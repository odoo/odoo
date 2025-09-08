# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, SUPERUSER_ID
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

        if self.env['res.groups']._is_feature_enabled('project.group_project_milestone'):
            service_policies.insert(1, ('delivered_milestones', _('Based on Milestones')))
        return service_policies

    service_tracking = fields.Selection(
        selection_add=[
            ('task_global_project', 'Task'),
            ('task_in_project', 'Project & Task'),
            ('project_only', 'Project'),
        ], ondelete={
            'task_global_project': 'set default',
            'task_in_project': 'set default',
            'project_only': 'set default',
        },
    )
    project_id = fields.Many2one(
        'project.project', 'Project', company_dependent=True, copy=True, domain='[("is_template", "=", False)]'
    )
    project_template_id = fields.Many2one(
        'project.project', 'Project Template', company_dependent=True, copy=True,
        domain='[("is_template", "=", True)]',
    )
    task_template_id = fields.Many2one('project.task', 'Task Template',
        domain="[('is_template', '=', True), ('project_id', '=', project_id)]",
        company_dependent=True, copy=True, compute='_compute_task_template', store=True, readonly=False
    )
    service_policy = fields.Selection('_selection_service_policy', string="Service Invoicing Policy", compute_sudo=True, compute='_compute_service_policy', inverse='_inverse_service_policy', tracking=True)
    service_type = fields.Selection(selection_add=[
        ('milestones', 'Project Milestones'),
    ])

    @api.depends('invoice_policy', 'service_type', 'type')
    def _compute_service_policy(self):
        for product in self:
            product.service_policy = self._get_general_to_service(product.invoice_policy, product.service_type)
            if not product.service_policy and product.type == 'service':
                product.service_policy = 'ordered_prepaid'

    @api.depends('project_id')
    def _compute_task_template(self):
        for product in self:
            if product.task_template_id and product.task_template_id.project_id != product.project_id:
                product.task_template_id = False

    @api.depends('service_policy')
    def _compute_product_tooltip(self):
        super()._compute_product_tooltip()

    def _prepare_service_tracking_tooltip(self):
        if self.service_tracking == 'task_global_project':
            return _("Create a task in an existing project to track the time spent.")
        elif self.service_tracking == 'project_only':
            return _(
                "Create an empty project for the order to track the time spent."
            )
        elif self.service_tracking == 'task_in_project':
            return _(
                "Create a project for the order with a task for each sales order line "
                "to track the time spent."
            )
        elif self.service_tracking == 'no':
            return _(
                "Create projects or tasks later, and link them to order to track the time spent."
            )
        return super()._prepare_service_tracking_tooltip()

    def _prepare_invoicing_tooltip(self):
        if self.service_policy == 'delivered_milestones':
            return _("Invoice your milestones when they are reached.")
        # ordered_prepaid and delivered_manual are handled in the super call, according to the
        # corresponding value in the `invoice_policy` field (delivered/ordered quantities)
        return super()._prepare_invoicing_tooltip()

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

    def write(self, vals):
        if 'type' in vals and vals['type'] != 'service':
            vals.update({
                'service_tracking': 'no',
                'project_id': False
            })
        return super().write(vals)

    @api.model
    def _get_saleable_tracking_types(self):
        return super()._get_saleable_tracking_types() + [
            'task_global_project',
            'task_in_project',
            'project_only',
        ]
