# -*- encoding: utf-8 -*-
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

import time
from openerp.report import report_sxw
from openerp.osv import osv


class order(report_sxw.rml_parse):

    def get_lines(self, user,objects):
        lines=[]
        for obj in objects:
            if user.id==obj.user_id.id:
                lines.append(obj)
        return lines

    def get_total(self, user,objects):
        lines=[]
        for obj in objects:
            if user.id==obj.user_id.id:
                lines.append(obj)
        total=0.0
        for line in lines:
            total+=line.price
        self.net_total+=total
        return total

    def get_nettotal(self):
        return self.net_total

    def get_users(self, objects):
        users=[]
        for obj in objects:
            if obj.user_id not in users:
                users.append(obj.user_id)
        return users

    def get_note(self,objects):
        notes=[]
        for obj in objects:
            notes.append(obj.note)
        return notes
        
    def __init__(self, cr, uid, name, context):
        super(order, self).__init__(cr, uid, name, context)
        self.net_total=0.0
        self.localcontext.update({
            'time': time,
            'get_lines': self.get_lines,
            'get_users': self.get_users,
            'get_total': self.get_total,
            'get_nettotal': self.get_nettotal,
            'get_note': self.get_note,
        })


class report_lunchorder(osv.AbstractModel):
    _name = 'report.lunch.report_lunchorder'
    _inherit = 'report.abstract_report'
    _template = 'lunch.report_lunchorder'
    _wrapped_report_class = order

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
