# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
import netsvc

class res_config_configurable(osv.osv_memory):
    _name = 'res.config'
    logger = netsvc.Logger()

    def _progress(self, cr, uid, context=None):
        total = self.pool.get('ir.actions.todo')\
            .search_count(cr, uid, [], context)
        open = self.pool.get('ir.actions.todo')\
            .search_count(cr, uid,[('type','=','configure'),
                                   ('active','=',True),
                                   ('state','<>','open')],
                          context)
        if total:
            return round(open*100./total)
        return 100.

    _columns = dict(
        progress=fields.float('Configuration Progress', readonly=True),
        )
    _defaults = dict(
        progress=_progress
        )

    def _next_action(self, cr, uid):
        todos = self.pool.get('ir.actions.todo')
        self.logger.notifyChannel('actions', netsvc.LOG_INFO,
                                  'getting next %s' % todos)
        active_todos = todos.search(cr, uid,
                                [('type','=','configure'),
                                 ('state', '=', 'open'),
                                 ('active','=',True)],
                                limit=1, context=None)
        if active_todos:
            return todos.browse(cr, uid, active_todos[0], context=None)
        return None

    def _next(self, cr, uid):
        self.logger.notifyChannel('actions', netsvc.LOG_INFO,
                                  'getting next operation')
        next = self._next_action(cr, uid)
        self.logger.notifyChannel('actions', netsvc.LOG_INFO,
                                  'next action is %s' % next)
        if next:
            self.pool.get('ir.actions.todo').write(cr, uid, next.id, {
                    'state':'done',
                    }, context=None)
            action = next.action_id
            return {
                'view_mode': action.view_mode,
                'view_type': action.view_type,
                'view_id': action.view_id and [action.view_id.id] or False,
                'res_model': action.res_model,
                'type': action.type,
                'target': action.target,
                }
        self.logger.notifyChannel(
            'actions', netsvc.LOG_INFO,
            'all configuration actions have been executed')
        return {'type': 'ir.actions.act_window_close'}
    def next(self, cr, uid, *args, **kwargs):
        return self._next(cr, uid)
res_config_configurable()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
