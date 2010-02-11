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

import wizard
import pooler

class event_edit_this(wizard.interface):
    event_form = """<?xml version="1.0"?>
                <form string="Edit this Occurence">
                    <separator string="" colspan="4" />
                    <newline />
                    <field name='name' colspan="4" />
                    <newline />
                    <field name='location' colspan="4" />
                    <newline />
                    <field name='date' />
                    <field name='date_deadline' />
                    <newline />
                    <field name='alarm_id'/>
                </form>"""

    event_fields = {
        'name': {'string': 'Title', 'type': 'char', 'size': 64}, 
        'date': {'string': 'Start Date', 'type': 'datetime'}, 
        'date_deadline': {'string': 'End Date', 'type': 'datetime'}, 
        'location': {'string': 'Location', 'type': 'char', 'size': 124}, 
        'alarm_id': {'string': 'Reminder', 'type': 'many2one', 'relation': 'res.alarm'}, 
    }
    
    def _default_values(self, cr, uid, data, context=None):
        model = data.get('model')
        model_obj = pooler.get_pool(cr.dbname).get(model)
        event = model_obj.read(cr, uid, data['id'], ['name', 'location', 'alarm_id'])
        event.update({
                      'date': context.get('date'), 
                      'date_deadline': context.get('date_deadline')
                      })
        return event

    def _modify_this(self, cr, uid, datas, context=None):
        model = datas.get('model')
        model_obj = pooler.get_pool(cr.dbname).get(model)
        new_id = model_obj.modify_this(cr, uid, [datas['id']], datas['form'], context)
        value = {
                'name': 'New event', 
                'view_type': 'form', 
                'view_mode': 'form,tree', 
                'res_model': model, 
                'res_id': new_id, 
                'view_id': False, 
                'type': 'ir.actions.act_window', 
            }
        return value

    states = {
        'init': {
            'actions': [_default_values], 
            'result': {'type': 'form', 'arch': event_form, 'fields': event_fields, 
                'state': [('end', 'Cancel', 'gtk-cancel'), ('edit', '_Save', 'gtk-save')]}
        }, 
        'edit': {
            'actions': [], 
            'result': {'type': 'action', 'action': _modify_this, 'state': 'end'}
        }
    }

event_edit_this('calendar.event.edit.this')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
