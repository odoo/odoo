# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_policy = fields.Selection([
        ('ordered_timesheet', 'Ordered quantities'),
        ('delivered_timesheet', 'Timesheets on tasks'),
        ('delivered_manual', 'Milestones (manually set quantities on order)')
    ], string="Service Invoicing Policy", compute='_compute_service_policy', inverse='_inverse_service_policy')
    service_type = fields.Selection(selection_add=[
        ('timesheet', 'Timesheets'),
    ])
    service_tracking = fields.Selection([
        ('no', 'Don\'t create task'),
    ], string="Service Tracking", default="no", help="On Sales order confirmation, this product can generate a project and/or task. From those, you can track the service you are selling.")

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
            if not policy and not product.invoice_policy == 'delivery':
                product.invoice_policy = 'order'
                product.service_type = 'manual'
            elif policy == 'ordered_timesheet':
                product.invoice_policy = 'order'
                product.service_type = 'timesheet'
            else:
                product.invoice_policy = 'delivery'
                product.service_type = 'manual' if policy == 'delivered_manual' else 'timesheet'

    @api.onchange('type')
    def _onchange_type(self):
        super(ProductTemplate, self)._onchange_type()
        if self.type == 'service':
            self.invoice_policy = 'order'
            self.service_type = 'timesheet'
        elif self.type == 'consu' and self.service_policy == 'ordered_timesheet':
            self.invoice_policy = 'order'
