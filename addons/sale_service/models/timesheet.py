# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, api, fields, exceptions
from openerp.tools.translate import _

class product_template(models.Model):
    _inherit = "product.template"
    project_id = fields.Many2one('project.project', string='Project', ondelete='set null')
    track_service = fields.Selection(selection_add=[('task', 'Create a task and track hours')])


class account_analytic_line(models.Model):
    _inherit = 'account.analytic.line'

    @api.model
    def _update_values(self, values):
        if values.get('task_id', False):
            task = self.env['project.task'].browse(values['task_id'])
            values['so_line'] = task.sale_line_id and task.sale_line_id.id or False

    @api.model
    def create(self, values):
        self._update_values(values)
        result = super(account_analytic_line, self).create(values)
        return result

    @api.multi
    def write(self, values):
        self._update_values(values)
        result = super(account_analytic_line, self).write(values)
        return result


