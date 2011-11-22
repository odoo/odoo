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

import time
from osv import osv
from osv import fields

class res_partner_event(osv.osv):
    _name = "res.partner.event"
    _columns = {
        'name': fields.char('Events', size=64, required=True),
        'description': fields.text('Description'),
        'partner_id': fields.many2one('res.partner', 'Partner', select=True),
        'date': fields.datetime('Date', size=16),
        'user_id': fields.many2one('res.users', 'User'),
    }
    _order = 'date desc'
    _defaults = {
        'date': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'),
        'user_id': lambda self, cr, uid, context: uid,
    }
res_partner_event()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
