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

from osv import osv, fields
from tools.translate import _

from document_ftp import ftpserver
class document_ftp_browse(osv.osv_memory):
    _name = 'document.ftp.browse'
    _description = 'Document FTP Browse'

    _columns = {
        'url' : fields.char('FTP Server', size=64, required=True),
    }

    def default_get(self, cr, uid, fields, context=None):
        res = {}
        if 'url' in fields:
            user_pool = self.pool.get('res.users')
            current_user = user_pool.browse(cr, uid, uid, context=context)
            res['url'] = 'ftp://%s@%s:%d'%(current_user.login, ftpserver.HOST, ftpserver.PORT)
        return res

    def browse_ftp(self, cr, uid, ids, context):
        data_id = ids and ids[0] or False
        data = self.browse(cr, uid, data_id, context)        
        final_url = data.url
        return {
        'type': 'ir.actions.act_url',
        'url':final_url,
        'target': 'new'
        }
document_ftp_browse()
    
