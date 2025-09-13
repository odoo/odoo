# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import threading

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _selection_service_policy(self):
        service_policies = super()._selection_service_policy()
        service_policies.insert(1, ('delivered_timesheet', _('Based on Timesheets')))
        return service_policies

    service_type = fields.Selection(selection_add=[
        ('timesheet', 'Timesheets on project (one fare per SO/Project)'),
    ], ondelete={'timesheet': 'set manual'})
    # override domain
    project_id = fields.Many2one(domain="['|', ('company_id', '=', False), '&', ('company_id', '=?', company_id), ('company_id', '=', current_company_id), ('allow_billable', '=', True), ('pricing_type', '=', 'task_rate'), ('allow_timesheets', 'in', [service_policy == 'delivered_timesheet', True])]")
    project_template_id = fields.Many2one(domain="['|', ('company_id', '=', False), '&', ('company_id', '=?', company_id), ('company_id', '=', current_company_id), ('allow_billable', '=', True), ('allow_timesheets', 'in', [service_policy == 'delivered_timesheet', True])]")
    service_upsell_threshold = fields.Float('Threshold', default=1, help="Percentage of time delivered compared to the prepaid amount that must be reached for the upselling opportunity activity to be triggered.")
    service_upsell_threshold_ratio = fields.Char(compute='_compute_service_upsell_threshold_ratio')

    @api.depends('uom_id', 'company_id')
    def _compute_service_upsell_threshold_ratio(self):
        product_uom_hour = self.env.ref('uom.product_uom_hour')
        uom_unit = self.env.ref('uom.product_uom_unit')
        company_uom = self.env.company.timesheet_encode_uom_id
        for record in self:
            if not record.uom_id or record.uom_id != uom_unit or\
               product_uom_hour.factor == record.uom_id.factor or\
               record.uom_id.category_id not in [product_uom_hour.category_id, uom_unit.category_id]:
                record.service_upsell_threshold_ratio = False
                continue
            else:
                timesheet_encode_uom = record.company_id.timesheet_encode_uom_id or company_uom
                record.service_upsell_threshold_ratio = f'(1 {record.uom_id.name} = {timesheet_encode_uom.factor / product_uom_hour.factor:.2f} {timesheet_encode_uom.name})'

    def _compute_visible_expense_policy(self):
        visibility = self.user_has_groups('project.group_project_user')
        for product_template in self:
            if not product_template.visible_expense_policy:
                product_template.visible_expense_policy = visibility
        return super(ProductTemplate, self)._compute_visible_expense_policy()

    @api.depends('service_tracking', 'service_policy', 'type', 'sale_ok')
    def _compute_product_tooltip(self):
        super()._compute_product_tooltip()
        for record in self.filtered(lambda record: record.type == 'service' and record.sale_ok):
            if record.service_policy == 'delivered_timesheet':
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

    @api.onchange('type', 'service_type', 'service_policy')
    def _onchange_service_fields(self):
        for record in self:
            default_uom_id = self.env['ir.default']._get_model_defaults('product.template').get('uom_id')
            default_uom = self.env['uom.uom'].browse(default_uom_id)
            if record.type == 'service' and record.service_type == 'timesheet' and \
               not (record._origin.service_policy and record.service_policy == record._origin.service_policy):
                if default_uom and default_uom.category_id == self.env.ref('uom.uom_categ_wtime'):
                    record.uom_id = default_uom
                else:
                    record.uom_id = self.env.ref('uom.product_uom_hour')
            elif record._origin.uom_id:
                record.uom_id = record._origin.uom_id
            elif default_uom:
                record.uom_id = default_uom
            else:
                record.uom_id = self._get_default_uom_id()
            record.uom_po_id = record.uom_id

    def _get_service_to_general_map(self):
        return {
            **super()._get_service_to_general_map(),
            'delivered_timesheet': ('delivery', 'timesheet'),
            'ordered_prepaid': ('order', 'timesheet'),
        }

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
            raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.', time_product.name))

    def write(self, vals):
        # timesheet product can't be archived or linked to a company
        test_mode = getattr(threading.current_thread(), 'testing', False) or self.env.registry.in_test_mode()
        if not test_mode and 'active' in vals and not vals['active']:
            time_product = self.env.ref('sale_timesheet.time_product')
            if time_product.product_tmpl_id in self:
                raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.', time_product.name))
        # TODO: avoid duplicate code by joining both conditions in master
        if not test_mode and 'company_id' in vals and vals['company_id']:
            time_product = self.env.ref('sale_timesheet.time_product')
            if time_product.product_tmpl_id in self:
                raise ValidationError(_('The %s product is required by the Timesheets app and cannot be linked to a company.', time_product.name))
        return super(ProductTemplate, self).write(vals)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @tools.ormcache()
    def _get_default_uom_id(self):
        return self.env.ref('uom.product_uom_unit')

    def _is_delivered_timesheet(self):
        """ Check if the product is a delivered timesheet """
        self.ensure_one()
        return self.type == 'service' and self.service_policy == 'delivered_timesheet'

    @api.onchange('type', 'service_type', 'service_policy')
    def _onchange_service_fields(self):
        for record in self:
            default_uom_id = self.env['ir.default']._get_model_defaults('product.product').get('uom_id')
            default_uom = self.env['uom.uom'].browse(default_uom_id)
            if record.type == 'service' and record.service_type == 'timesheet' and \
               not (record._origin.service_policy and record.service_policy == record._origin.service_policy):
                if default_uom and default_uom.category_id == self.env.ref('uom.uom_categ_wtime'):
                    record.uom_id = default_uom
                else:
                    record.uom_id = self.env.ref('uom.product_uom_hour')
            elif record._origin.uom_id:
                record.uom_id = record._origin.uom_id
            elif default_uom:
                record.uom_id = default_uom
            else:
                record.uom_id = self._get_default_uom_id()
            record.uom_po_id = record.uom_id

    @api.onchange('service_policy')
    def _onchange_service_policy(self):
        self._inverse_service_policy()
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
            raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.', time_product.name))

    def write(self, vals):
        # timesheet product can't be archived
        test_mode = getattr(threading.current_thread(), 'testing', False) or self.env.registry.in_test_mode()
        if not test_mode and 'active' in vals and not vals['active']:
            time_product = self.env.ref('sale_timesheet.time_product')
            if time_product in self:
                raise ValidationError(_('The %s product is required by the Timesheets app and cannot be archived nor deleted.', time_product.name))
        return super(ProductProduct, self).write(vals)
