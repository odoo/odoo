# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

class knowledge_config_settings(osv.osv_memory):
    _name = 'knowledge.config.settings'
    _inherit = 'res.config.settings'
    _columns = {
        'module_wiki_faq': fields.boolean('Internal FAQ as a Wiki',
            help="""This installs the module wiki_faq."""), 
        'module_wiki_quality_manual': fields.boolean('Quality Manual as a Wiki',
            help="""This installs the module wiki_quality_manual."""),
        'module_document': fields.boolean('Document Management',
            help="""This is a complete document management system, with: user authentication,
                full document search (but pptx and docx are not supported), and a document dashboard.
                This installs the module document."""),
        'module_document_ftp': fields.boolean('Share repositories (FTP)',
            help="""Access your documents in OpenERP through an FTP interface.
                This installs the module document_ftp."""),
        'module_document_webdav': fields.boolean('Share Repositories (WebDAV)',
            help="""Access your documents in OpenERP through WebDAV.
                This installs the module document_webdav."""),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
