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

from osv import osv
from osv import fields


class google_import_message(osv.osv):
    """Import Message"""
    
    _name = "google.import.message"
    _description = "Import Message"
    _columns = {
        'name': fields.text('Message', readonly=True),
        }

    def default_get(self, cr, uid, fields, context=None):
        if context == None:
            context = {}
        res = super(google_import_message, self).default_get(cr, uid, fields, context=context)
        res.update({'name': context.get('message')})
        return res

google_import_message()
