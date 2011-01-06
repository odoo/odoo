# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution    
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import wizard
import tools
import pooler

def _launch_url(self, cr, uid, data, context):
    port = tools.config.get('ftp_server_port','8021')
    url = 'ftp://localhost'
    pool_obj = pooler.get_pool(cr.dbname)
    model_data_obj = pool_obj.get('ir.model.data')
    aid = model_data_obj._get_id(cr, uid, 'document', 'action_document_browse')
    aid = model_data_obj.browse(cr, uid, aid, context=context).res_id
    url_read = pool_obj.get('ir.actions.url').read(cr, uid, [aid], ['url'], context=context)
    url_ftp = url_read[0]['url'].rfind(':')
    if url_ftp:
        url = url_read[0]['url'][:url_ftp]
    final_url = url + ':' + str(port)
    return {
    'type': 'ir.actions.act_url',
    'url':final_url,
    'target': 'new'
    }
class wizard_browse_files_ftp(wizard.interface):
    
    states= {'init' : {'actions': [],
                       'result':{'type':'action',
                                 'action': _launch_url,
                                 'state':'end'}
                       }
             }
wizard_browse_files_ftp('browse.file.ftp')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
