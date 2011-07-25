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

from osv import fields,osv


class res_widget(osv.osv):
    _name = "res.widget"
    _rec_name = "title"
    _columns = {
        'title' : fields.char('Title', size=64, required=True, translate=True),
        'content': fields.text('Content', required=True),
    }

res_widget()


class res_widget_user(osv.osv):
    _name="res.widget.user"
    _order = "sequence"
    _columns = {
        'sequence': fields.integer('Sequence'),
        'user_id': fields.many2one('res.users','User', select=1, ondelete='cascade'),
        'widget_id': fields.many2one('res.widget','Widget',required=True, ondelete='cascade'),
    }

    def create(self, cr, uid, vals, context=None):
        existing = self.search(cr, uid, [('user_id', '=', vals.get('user_id')), ('widget_id', '=', vals.get('widget_id'))], context=context)
        if existing:
            res = existing[0]
        else:
            res = super(res_widget_user, self).create(cr, uid, vals, context=context)
        return res

res_widget_user()

class res_widget_wizard(osv.osv_memory):
    _name = "res.widget.wizard"
    _description = "Add a widget for User"
    
    def widgets_list_get(self, cr, uid,context=None):
        widget_obj=self.pool.get('res.widget')
        ids=widget_obj.search(cr, uid,[],context=context)
        if not len(ids):
            return []
        reads = widget_obj.read(cr, uid, ids, ['title'], context=context)
        res = []
        for record in reads:
            res.append((record['id'], record['title']))
        return res

    _columns = {
        'widgets_list': fields.selection(widgets_list_get,string='Widget',required=True),
    }

    def action_get(self, cr, uid, context=None):
        return self.pool.get('ir.actions.act_window').for_xml_id(
            cr, uid, 'base', 'action_res_widget_wizard', context=context)

    def res_widget_add(self, cr, uid, ids, context=None):
        widget_id = self.read(cr, uid, ids, context=context)[0]
        if widget_id.has_key('widgets_list') and widget_id['widgets_list']:
            self.pool.get('res.widget.user').create(
                cr, uid, {'user_id':uid, 'widget_id':widget_id['widgets_list']}, context=context)
        return {'type': 'ir.actions.act_window_close'}

res_widget_wizard()

