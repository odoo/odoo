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
        'module_document_webdav': fields.boolean('Share Repositories (WebDAV)',
                           help ="""It install the document_webdav."""),                                   
    }
knowledge_configuration()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: