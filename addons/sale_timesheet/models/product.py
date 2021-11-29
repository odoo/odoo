# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

SERVICE_POLICY = [
    # (service_policy, (invoice_policy, service_type), string)
    ('ordered_timesheet', ('order', 'timesheet'), 'Prepaid/Fixed Price'),
    ('delivered_timesheet', ('delivery', 'timesheet'), 'Based on Timesheets'),
    ('delivered_manual', ('delivery', 'manual'), 'Based on Milestones'),
]
SERVICE_TO_GENERAL = {policy[0]: policy[1] for policy in SERVICE_POLICY}
GENERAL_TO_SERVICE = {policy[1]: policy[0] for policy in SERVICE_POLICY}


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_policy = fields.Selection([
        (policy[0], policy[2]) for policy in SERVICE_POLICY
    ], string="Service Invoicing Policy", compute='_compute_service_policy', inverse='_inverse_service_policy')
    service_type = fields.Selection(selection_add=[
        ('timesheet', 'Timesheets on project (one fare per SO/Project)'),
    ], ondelete={'timesheet': 'set default'})
    # override domain
    project_id = fields.Many2one(domain="[('company_id', '=', current_company_id), ('allow_billable', '=', True), ('pricing_type', '=', 'task_rate'), ('allow_timesheets', 'in', [service_policy == 'delivered_timesheet', True])]")
    project_template_id = fields.Many2one(domain="[('company_id', '=', current_company_id), ('allow_billable', '=', True), ('allow_timesheets', 'in', [service_policy == 'delivered_timesheet', True])]")
    service_upsell_threshold = fields.Float('Threshold', default=1, help="Percentage of time delivered compared to the prepaid amount that must be reached for the upselling opportunity activity to be triggered.")
    service_upsell_threshold_ratio = fields.Char(compute='_compute_service_upsell_threshold_ratio')

    @api.depends('uom_id')
    def _compute_service_upsell_threshold_ratio(self):
        product_uom_hour = self.env.ref('uom.product_uom_hour')
        for record in self:
            if not record.uom_id:
                record.service_upsell_threshold_ratio = False
                continue
            record.service_upsell_threshold_ratio = f"1 {record.uom_id.name} = {product_uom_hour.factor / record.uom_id.factor:.2f} Hours"

    def _compute_visible_expense_policy(self):
        visibility = self.user_has_groups('project.group_project_user')
        for product_template in self:
            if not product_template.visible_expense_policy:
                product_template.visible_expense_policy = visibility
        return super(ProductTemplate, self)._compute_visible_expense_policy()

    @api.depends('invoice_policy', 'service_type', 'type')
    def _compute_service_policy(self):
        for product in self:
            product.service_policy = GENERAL_TO_SERVICE.get((product.invoice_policy, product.service_type), False)
            if not product.service_policy and product.type == 'service':
                product.service_policy = 'ordered_timesheet'

    @api.onchange('service_policy')
    def _inverse_service_policy(self):
        for product in self:
            if product.service_policy:
                product.invoice_policy, product.service_type = SERVICE_TO_GENERAL.get(product.service_policy, (False, False))

    @api.depends('service_tracking', 'service_policy', 'type')
    def _compute_product_tooltip(self):
        super()._compute_product_tooltip()
        for record in self.filtered(lambda record: record.type == 'service'):
            if record.service_policy == 'ordered_timesheet':
                pass
            elif record.service_policy == 'delivered_timesheet':
                if record.service_tracking == 'no':
                    record.product_tooltip = _(
                        "Invoice based on timesheets (delivered quantity) on projects or tasks "
                        "you'll create later on."
                    )
                elif record.service_tracking == 'task_global_project':
                    record.product_tooltip = _(
                        "Invoice based on timesheets (delivered quantity), and create a task in "
                        "an existing project to track the time spent."
                    )
                elif record.service_tracking == 'task_in_project':
                    record.product_tooltip = _(
                        "Invoice based on timesheets (delivered quantity), and create a project "
                        "for the order with a task for each sales order line to track the time "
                        "spent."
                    )
                elif record.service_tracking == 'project_only':
                    record.product_tooltip = _(
                        "Invoice based on timesheets (delivered quantity), and create an empty "
                        "project for the order to track the time spent."
                    )
            elif record.service_policy == 'delivered_manual':
                if record.service_tracking == 'no':
                    record.product_tooltip = _(
                        "Sales order lines define milestones of the project to invoice by setting "
                        "the delivered quantity."
                    )
                elif record.service_tracking == 'task_global_project':
                    record.product_tooltip = _(
                        "Sales order lines define milestones of the project to invoice by setting "
                        "the delivered quantity. Create a task in an existing project to track the"
                        " time spent."
                    )
                elif record.service_tracking == 'task_in_project':
                    record.product_tooltip = _(
                        "Sales order lines define milestones of the project to invoice by setting "
                        "the delivered quantity. Create an empty project for the order to track "
                        "the time spent."
                    )
                elif record.service_tracking == 'project_only':
                    record.product_tooltip = _(
                        "Sales order lines define milestones of the project to invoice by setting "
                        "the delivered quantity. Create a project for the order with a task for "
                        "each sales order line to track the time spent."
                    )

    @api.model
    def _get_onchange_service_policy_updates(self, service_tracking, service_policy, project_id, project_template_id):
        vals = {}
        if service_tracking != 'no' and service_policy == 'delivered_timesheet':
            if project_id and not project_id.allow_timesheets:
                vals['project_id'] = False
            elif project_template_id and not project_template_id.allow_timesheets:
                vals['project_template_id'] = False
        return vals

    @api.onchange('service_policy')
    def _onchange_service_policy(self):
        self._inverse_service_policy()
        vals = self._get_onchange_service_policy_updates(self.service_tracking,
                                                        self.service_policy,
                                                        self.project_id,
                                                        self.project_template_id)
        if vals:
            self.update(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        time_product = self.env.ref('sale_timesheet.time_product')
        if time_product.product_tmpl_id in self:
            raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.') % time_product.name)

    def write(self, vals):
        # timesheet product can't be archived
        test_mode = getattr(threading.currentThread(), 'testing', False) or self.env.registry.in_test_mode()
        if not test_mode and 'active' in vals and not vals['active']:
            time_product = self.env.ref('sale_timesheet.time_product')
            if time_product.product_tmpl_id in self:
                raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.') % time_product.name)
        return super(ProductTemplate, self).write(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _is_delivered_timesheet(self):
        """ Check if the product is a delivered timesheet """
        self.ensure_one()
        return self.type == 'service' and self.service_policy == 'delivered_timesheet'

    @api.onchange('service_policy')
    def _onchange_service_policy(self):
        self.product_tmpl_id._inverse_service_policy()
        vals = self.product_tmpl_id._get_onchange_service_policy_updates(self.service_tracking,
                                                                        self.service_policy,
                                                                        self.project_id,
                                                                        self.project_template_id)
        if vals:
            self.update(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_master_data(self):
        time_product = self.env.ref('sale_timesheet.time_product')
        if time_product in self:
            raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.') % time_product.name)

    def write(self, vals):
        # timesheet product can't be archived
        test_mode = getattr(threading.currentThread(), 'testing', False) or self.env.registry.in_test_mode()
        if not test_mode and 'active' in vals and not vals['active']:
            time_product = self.env.ref('sale_timesheet.time_product')
            if time_product in self:
                raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.') % time_product.name)
        return super(ProductProduct, self).write(vals)
