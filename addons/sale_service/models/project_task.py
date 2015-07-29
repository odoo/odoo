# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv


class ProjectTaskStageMrp(osv.Model):
    """ Override project.task.type model to add a 'closed' boolean field allowing
        to know that tasks in this stage are considered as closed. Indeed since
        OpenERP 8.0 status is not present on tasks anymore, only stage_id. """
    _name = 'project.task.type'
    _inherit = 'project.task.type'

    _columns = {
        'closed': fields.boolean('Is a close stage', help="Tasks in this stage are considered as closed."),
    }

    _defaults = {
        'closed': False,
    }


class project_task(osv.osv):
    _name = "project.task"
    _inherit = "project.task"
    _columns = {
        'procurement_id': fields.many2one('procurement.order', 'Procurement', ondelete='set null'),
        'sale_line_id': fields.related('procurement_id', 'sale_line_id', type='many2one', relation='sale.order.line', store=True, string='Sales Order Line'),
    }

    def _validate_subflows(self, cr, uid, ids, context=None):
        proc_obj = self.pool.get("procurement.order")
        for task in self.browse(cr, uid, ids, context=context):
            if task.procurement_id:
                proc_obj.check(cr, uid, [task.procurement_id.id], context=context)

    def write(self, cr, uid, ids, values, context=None):
        """ When closing tasks, validate subflows. """
        res = super(project_task, self).write(cr, uid, ids, values, context=context)
        if values.get('stage_id'):
            stage = self.pool.get('project.task.type').browse(cr, uid, values.get('stage_id'), context=context)
            if stage.closed:
                self._validate_subflows(cr, uid, ids, context=context)
        return res
