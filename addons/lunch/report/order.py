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
from openerp.addons.web import http
from openerp.addons.web.http import request


class order(http.Controller):

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
        
    @http.route(['/report/lunch.report_lunchorder/<docids>'], type='http', auth='user', website=True, multilang=True)
    def report_lunch(self, docids):
        self.cr, self.uid, self.context = request.cr, request.uid, request.context

        ids = [int(i) for i in docids.split(',')]
        report_obj = request.registry['lunch.order.line']
        docs = report_obj.browse(self.cr, self.uid, ids, context=self.context)

        self.net_total=0.0
        docargs = {
            'docs': docs,
            'time': time,
            'get_lines': self.get_lines,
            'get_users': self.get_users,
            'get_total': self.get_total,
            'get_nettotal': self.get_nettotal,
            'get_note': self.get_note,
        }
        return request.registry['report'].render(self.cr, self.uid, [], 'lunch.report_lunchorder', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
