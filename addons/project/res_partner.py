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

from openerp.osv import fields,osv

class res_partner(osv.osv):
    def _task_count(self, cr, uid, ids, field_name, arg, context=None):
        Task = self.pool['project.task']
        return {
            partner_id: Task.search_count(cr,uid, [('partner_id', '=', partner_id)], context=context)
            for partner_id in ids
        }
    
    """ Inherits partner and adds Tasks information in the partner form """
    _inherit = 'res.partner'
    _columns = {
        'task_ids': fields.one2many('project.task', 'partner_id', 'Tasks'),
        'task_count': fields.function(_task_count, string='# Tasks', type='integer'),
    }

    def copy(self, cr, uid, record_id, default=None, context=None):
        if default is None:
            default = {}

        default['task_ids'] = []
        return super(res_partner, self).copy(
                cr, uid, record_id, default=default, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
