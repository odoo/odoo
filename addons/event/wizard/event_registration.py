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

class event_registration_list(osv.osv_memory):
    """ List Event Registration """
    _name = "event.registration.list"
    _description = "List Event Registrations"

    def open_registration(self, cr, uid, ids, context={}):
        cr.execute('SELECT section_id FROM event_event WHERE id = %s', (context['active_id'],))
        res = cr.fetchone()
        return {
            'domain': [('section_id', '=', res[0])],
            'name': 'Event Registrations',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'event.registration',
            'type': 'ir.actions.act_window'
        }

event_registration_list()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: