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
from tools import config

class documnet_ftp_setting(osv.osv_memory):
    _name = 'knowledge.configuration'
    _inherit = 'knowledge.configuration'
    _columns = {
        'url': fields.char('Borwse Documents',size=64,
                           help ="""It allow to browse the document from the relative URL""", readonly=True),               
    }

    def get_default_ftp_config(self, cr, uid, ids, context=None):
        ir_values = self.pool.get('ir.actions.url')
        user_pool = self.pool.get('res.users')
        current_user = user_pool.browse(cr, uid, uid, context=context)
        data_pool = self.pool.get('ir.model.data')
        aid = data_pool._get_id(cr, uid, 'document_ftp', 'action_document_browse')
        aid = data_pool.browse(cr, uid, aid, context=context).res_id
        ftp_url = self.pool.get('ir.actions.url').browse(cr, uid, aid, context=context)
        url = ftp_url.url and ftp_url.url.split('ftp://') or []
        if url:
            url = url[1]
            if url[-1] == '/':
                url = url[:-1]
        else:
            url = '%s:%s' %(ftpserver.HOST, ftpserver.PORT) 
        return {'url':'ftp://%s@%s'%(current_user.login, url)}
                            
    def document_ftp(self, cr, uid, ids, context=None):
        data_id = ids and ids[0] or False
        data = self.browse(cr, uid, data_id, context=context)
        return {
        'type': 'ir.actions.act_url',
        'url':data.url,
        'nodestroy':True,
        } 
     
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: