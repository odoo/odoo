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

from osv import fields,osv,orm

class res_partner_address(osv.osv):
    _inherit = "res.partner.address"

    _columns = {
        'last_modification_date': fields.datetime('Last Modification Date', readonly=True, help="Last modification date of google contact."),
    }

    def unlink(self, cr, uid, ids, context=None):
        model_obj = self.pool.get('ir.model.data')
        model_ids = model_obj.search(cr, uid, [('res_id','in',ids),('model','=','res.partner.address'),('module','=','sync_google_contact')], context=context)
        model_obj.unlink(cr, uid, model_ids, context=context)
        return super(res_partner_address, self).unlink(cr, uid, ids, context=context)

res_partner_address()

# vim:expandtab:smartindent:toabstop=4:softtabstop=4:shiftwidth=4:
