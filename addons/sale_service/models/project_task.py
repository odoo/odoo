# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class ProjectTaskStageMrp(models.Model):
    """ Override project.task.type model to add a 'closed' boolean field allowing
        to know that tasks in this stage are considered as closed. Indeed since
        OpenERP 8.0 status is not present on tasks anymore, only stage_id. """
    _inherit = 'project.task.type'

    closed = fields.Boolean(string='Is a close stage', default=False, help="Tasks in this stage are considered as closed.")


class ProjectTask(models.Model):
    _inherit = "project.task"

    procurement_id = fields.Many2one('procurement.order', string='Procurement', ondelete='set null')
    sale_line_id = fields.Many2one(related='procurement_id.sale_line_id', relation='sale.order.line', store=True, string='Sales Order Line')

    @api.multi
    def _validate_subflows(self):
        for task in self.filtered(lambda task: task.procurement_id):
            task.procurement_id.check()

    @api.multi
    def write(self, values):
        """ When closing tasks, validate subflows. """
        result = super(ProjectTask, self).write(values)
        if self.stage_id and self.stage_id.closed:
            self._validate_subflows()
        return result
