# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    track_service = fields.Selection(selection_add=[
        ('timesheet', 'Timesheets on project'),
        ('task', 'Create a task per order line to track hours')])
    project_id = fields.Many2one(
        'project.project', 'Project', company_dependent=True,
        help='Create a task under this project on sales order validation. This setting must be set for each company.')

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'service':
            self.track_service = 'timesheet'
        else:
            self.track_service = 'manual'


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _need_procurement(self):
        for product in self:
            if product.type == 'service' and product.track_service == 'task':
                return True
        return super(ProductProduct, self)._need_procurement()
