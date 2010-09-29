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

class mail_gateway_document(osv.osv_memory):
    """ Mail Gateway Document """
    _name = "mail.gateway.document"
    _description = "Mail Gateway Document"


    def open_document(self, cr, uid, ids, context):
        """ To Open Document
        @param self: The object pointer.
        @param cr: A database cursor
        @param uid: ID of the user currently logged in
        @param ids: the ID or list of IDs if we want more than one
        @param context: A standard dictionary
        """
        result = []
        document_id = context.get('active_id', False)
        mailgate_obj = self.pool.get('mailgate.message')
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')
        mailgate_data = mailgate_obj.browse(cr, uid, document_id)
        model = mailgate_data.model
        res_id = mailgate_data.res_id

        view_obj = self.pool.get('ir.ui.view')
        view_id = view_obj.search(cr, uid, [('model', '=', model),('type','=','tree')])
        return {
            'domain' : "[('id','=',%d)]"%(res_id),
            'view_mode': 'tree,form',
            'view_type': 'form',
            'view_id': view_id or False,
            'res_model': model,
            'res_id': res_id,
            'context': context,
            'type': 'ir.actions.act_window',
            }

mail_gateway_document()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
