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

class res_widget_wizard(osv.osv_memory):
    _name = "res.widget.wizard"
    _description = "Res Widget Wizard"

    _columns = {
        'res_widget': fields.one2many("res.widget", 'widget_res', 'Res Widget', required=True),
    }

    def res_widget_add(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        res_widget = self.read(cr, uid, ids)[0]
        self.pool.get('res.widget').write(cr, uid, res_widget['res_widget'],{'widget_res':context['active_ids'][0]})
        return {}
        
res_widget_wizard()