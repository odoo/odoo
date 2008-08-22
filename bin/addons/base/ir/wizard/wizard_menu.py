# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2008 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id$
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from osv import fields,osv

class wizard_model_menu(osv.osv_memory):
    _name = 'wizard.ir.model.menu.create'
    _columns = {
        'model_id': fields.many2one('ir.model','Object', required=True),
        'menu_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
        'name': fields.char('Menu Name', size=64, required=True),
        'view_ids': fields.one2many('wizard.ir.model.menu.create.line', 'wizard_id', 'Views'),
    }
    _defaults = {
        'model_id': lambda self,cr,uid,ctx: ctx.get('model_id', False)
    }
    def menu_create(self, cr, uid, ids, context={}):
        for menu in self.browse(cr, uid, ids, context):
            view_mode = []
            views = []
            for view in menu.view_ids:
                view_mode.append(view.view_type)
                views.append( (0,0,{
                    'view_id': view.view_id and view.view_id.id or False,
                    'view_mode': view.view_type,
                    'sequence': view.sequence
                }))
            val = {
                'name': menu.name,
                'res_model': menu.model_id.model,
                'view_type': 'form',
                'view_mode': ','.join(view_mode)
            }
            if views:
                val['view_ids'] = views
            else:
                val['view_mode'] = 'tree,form'
            action_id = self.pool.get('ir.actions.act_window').create(cr, uid, val)
            self.pool.get('ir.ui.menu').create(cr, uid, {
                'name': menu.name,
                'parent_id': menu.menu_id.id,
                'action': 'ir.actions.act_window,%d' % (action_id,),
                'icon': 'STOCK_INDENT'
            }, context)
        return {'type':'ir.actions.act_window_close'}
wizard_model_menu()

class wizard_model_menu_line(osv.osv_memory):
    _name = 'wizard.ir.model.menu.create.line'
    _columns = {
        'wizard_id': fields.many2one('wizard.ir.model.menu.create','Wizard'),
        'sequence': fields.integer('Sequence'),
        'view_type': fields.selection([('tree','Tree'),('form','Form'),('graph','Graph'),('calendar','Calendar')],'View Type',required=True),
        'view_id': fields.many2one('ir.ui.view', 'View'),
    }
    _defaults = {
        'view_type': lambda self,cr,uid,ctx: 'tree'
    }
wizard_model_menu_line()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

