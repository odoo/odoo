# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    track_service = fields.Selection(selection_add=[('timesheet', 'Timesheets on project'), ('task', 'Create a task and track hours')])
    project_id = fields.Many2one('project.project', string='Project',
                                 help='Create a task under this project on sale order validation. This setting must be set for each company.',
                                 company_dependent=True)

    @api.onchange('type', 'invoice_policy')
    def onchange_type_timesheet(self):
        if self.type == 'service':
            self.track_service = 'timesheet'
        else:
            self.track_service = 'manual'
        return {}


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.multi
    def _need_procurement(self):
        for product in self:
            if product.type == 'service' and product.track_service == 'task':
                return True
        return super(ProductProduct, self)._need_procurement()
