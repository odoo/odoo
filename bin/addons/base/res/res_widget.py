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
        'title' : fields.char('Title', size=64, required=True),
        'content': fields.text('Content', required=True),
    }
res_widget()

class res_widget_user(osv.osv):
    _name="res.widget.user"
    _columns = {
        'sequence': fields.integer('Sequence'),
        'user_id': fields.many2one('res.users','User'),
        'widget_id': fields.many2one('res.widget','Widget'),
    }
res_widget_user()

