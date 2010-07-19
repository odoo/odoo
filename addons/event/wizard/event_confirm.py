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

class event_confirm(osv.osv_memory):
    """
    Confirm Event
    """
    _name = "event.confirm"
    _description = "Event Confirmation"

    _columns = {
        'msg': fields.text('Message', readonly=True),
    }
    _defaults = {
        'msg': _('Warning: This Event has not reached its Minimum Registration Limit. Are you sure you want to confirm it?')
    }

    def confirm(self, cr, uid, ids, context):
        event_pool = self.pool.get('event.event')
        event_ids = context.get('event_ids', [])
        event_pool.do_confirm(cr, uid, event_ids, context=context)
        return {}

event_confirm()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
