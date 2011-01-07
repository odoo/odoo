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
from tools.translate import _

class event_confirm_registration(osv.osv_memory):
    """
    Confirm Event Registration
    """
    _name = "event.confirm.registration"
    _description = "Confirmation for Event Registration"

    _columns = {
        'msg': fields.text('Message', readonly=True),
     }
    _defaults = {
        'msg': 'The event limit is reached. What do you want to do?'
     }

    def default_get(self, cr, uid, fields, context=None):
        """
        This function gets default values
        """
        if context is None:
            context = {}
        registration_pool = self.pool.get('event.registration')
        registration_ids = context.get('registration_ids', [])
        res = super(event_confirm_registration, self).default_get(cr, uid, fields, context=context)
        msg = ""
        overlimit_event_ids = []
        for registration in registration_pool.browse(cr, uid, registration_ids, context=context):
            register_max = registration.event_id.register_max
            if registration.event_id.id not in overlimit_event_ids:
                overlimit_event_ids.append(registration.event_id.id)
                msg += _("Warning: The Event '%s' has reached its Maximum Limit (%s).") \
                            %(registration.event_id.name, register_max)
        if 'msg' in fields:
            res.update({'msg': msg})
        return res

    def confirm(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        registration_pool = self.pool.get('event.registration')
        registration_ids = context.get('registration_ids', [])
        registration_pool.do_open(cr, uid, registration_ids, context=context)
        return {'type': 'ir.actions.act_window_close'}

event_confirm_registration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: