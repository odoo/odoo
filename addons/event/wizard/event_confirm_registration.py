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

class event_confirm_registration(osv.osv_memory):
    """
    Confirm Event Registration
    """
    _name = "event.confirm.registration"
    _description = "Event Registraion"
    _columns = {
        'msg': fields.text('Message', readonly=True),
               }
    _defaults={
       'msg':lambda *a:'The event limit is reached. What do you want to do?'
               }

    def confirm(self, cr, uid, ids, context):
        registration_obj = self.pool.get('event.registration')
        reg_id = context.get('reg_id', False) or context.get('active_id', False)
        if reg_id:
            registration_obj.write(cr, uid, [reg_id], {'state':'open',})
            registration_obj._history(cr, uid, [reg_id], 'Open', history=True)
            registration_obj.mail_user(cr,uid,[reg_id])
        return {}

event_confirm_registration()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: