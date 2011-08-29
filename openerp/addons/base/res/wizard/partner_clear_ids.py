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

import netsvc
from osv import fields, osv

class partner_clear_ids(osv.osv_memory):
    """ Clear IDs """

    _name = "partner.clear.ids"
    _description = "Clear IDs"

    def clear_ids(self, cr, uid, ids, context):
        """
           Clear Ids

            @param cr: the current row, from the database cursor.
            @param uid: the current user’s ID for security checks.
            @param ids: the ID or list of IDs
            @param context: A standard dictionary
        """

        partner_pool = self.pool.get('res.partner')
        active_ids = context and context.get('active_ids', [])
        res = {}
        for partner in partner_pool.browse(cr, uid, active_ids, context=context):
            if active_ids in partner:
                res.update({'ref': False})
        return res

partner_clear_ids()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

