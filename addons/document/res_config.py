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
from lxml import etree

class knowledge_configuration(osv.osv_memory):
    _name = 'knowledge.configuration'
    _inherit = 'res.config.settings'
    
    _columns = {
        'module_wiki_quality_manual': fields.boolean('Use an internal wiki to group FAQ',
                           help ="""It installs the wiki_quality_manual module."""),
        'module_wiki_faq': fields.boolean('Track quality with wiki',
                           help ="""It install the wiki_faq."""), 
        'module_document_ftp': fields.boolean('Share repositories (FTP)',
                           help ="""It install the document_ftp."""),
        'server_address_port': fields.char('Server address/IP and port',size=128,
                           help ="""It assign server address/IP and port."""),               
        'module_document_webdav': fields.boolean('Share Repositories (WebDAV)',
                           help ="""It install the document_webdav."""),                                   
                             
    }
    
    _defaults = {
        'server_address_port': config.get('ftp_server_host', 'localhost') + ':' + config.get('ftp_server_port', '8021'),
    }
              
    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        res = super(knowledge_configuration, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=False)
        ir_module = self.pool.get('ir.module.module')
        module_id= ir_module.search(cr, uid, [('name','=','document_ftp')])
        modle_state = ir_module.browse(cr,uid, module_id[0],context=context).state
        doc = etree.XML(res['arch'])
        nodes = doc.xpath("//field[@name='server_address_port']")
        if modle_state == 'uninstalled':
            for node in nodes:
                node.set('invisible', '1')
            res['arch'] = etree.tostring(doc)
        return res
    
    def set_ftp_configurations(self, cr, uid, ids, context=None):
        data_pool = self.pool.get('ir.model.data')
        ir_module = self.pool.get('ir.module.module')
        module_id= ir_module.search(cr, uid, [('name','=','document_ftp')])
        modle_state = ir_module.browse(cr,uid, module_id[0],context=context).state
        if modle_state == 'installed':
            conf = self.browse(cr, uid, ids[0], context=context)
            doc_id = data_pool._get_id(cr, uid, 'document_ftp', 'action_document_browse')
            doc_ids = data_pool.browse(cr, uid, doc_id, context=context).res_id
            self.pool.get('ir.actions.url').write(cr, uid, [doc_ids], {'url': 'ftp://'+(conf.server_address_port or 'localhost:8021')+'/' + cr.dbname+'/'})
        return True
        
knowledge_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: