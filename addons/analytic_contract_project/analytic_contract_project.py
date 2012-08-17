# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from tools.translate import _

class project_project(osv.osv):
    _inherit = 'project.project'

    _defaults = {
        'use_timesheets': True,
    }

    def open_sale_order_lines(self,cr,uid,ids,context=None):
        account_ids = [x.analytic_account_id.id for x in self.browse(cr, uid, ids, context=context)]
        return self.pool.get('account.analytic.account').open_sale_order_lines(cr, uid, account_ids, context=context)

    def open_timesheets_to_invoice(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        analytic_account_id = self.browse(cr, uid, ids[0], context=context).analytic_account_id.id
        context.update({'search_default_account_id': analytic_account_id, 'default_account_id': analytic_account_id, 'search_default_to_invoice': 1})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Timesheet Lines to Invoice'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': context,
            'domain' : [('invoice_id','=',False),('to_invoice','!=',False), ('journal_id.type', '=', 'general')],
            'res_model': 'account.analytic.line',
            'nodestroy': True,
        }

    def open_timesheets(self, cr, uid, ids, context=None):
        """ open Timesheets view """
        project = self.browse(cr, uid, ids[0], context)
        try:
            journal_id = self.pool.get('ir.model.data').get_object(cr, uid, 'hr_timesheet', 'analytic_journal').id
        except ValueError:
            journal_id = False
        view_context = {
            'search_default_account_id': [project.analytic_account_id.id],
            'default_account_id': project.analytic_account_id.id,
            'default_journal_id': journal_id,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bill Tasks Works'),
            'res_model': 'account.analytic.line',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'context': view_context,
            'nodestroy': True,
        }
project_project()

class task(osv.osv):
    _inherit = "project.task"
    
    def create(self, cr, uid, vals, context=None):
        task_id = super(task, self).create(cr, uid, vals, context=context)
        task_browse = self.browse(cr, uid, task_id, context=context)
        if task_browse.project_id.analytic_account_id:
            self.pool.get('account.analytic.account').message_post(cr, uid, [task_browse.project_id.analytic_account_id.id], body=_("Task <em>%s</em> has been <b>created</b>.") % (task_browse.name), context=context)
        return task_id
task()
