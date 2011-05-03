# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class knowledge_installer(osv.osv_memory):
    _inherit = 'base.setup.installer'

    _columns = {
        # Knowledge Management
        'document_ftp':fields.boolean('Shared Repositories (FTP)',
            help="Provides an FTP access to your OpenERP's "
                "Document Management System. It lets you access attachments "
                "and virtual documents through a standard FTP client."),
        'document_webdav':fields.boolean('Shared Repositories (WebDAV)',
            help="Provides a WebDAV access to your OpenERP's Document "
                 "Management System. Lets you access attachments and "
                 "virtual documents through your standard file browser."),
        'wiki':fields.boolean('Collaborative Content (Wiki)',
            help="Lets you create wiki pages and page groups in order "
                 "to keep track of business knowledge and share it with "
                 "and  between your employees."),
        # Content templates
        'wiki_faq':fields.boolean('Template: Internal FAQ',
            help="Creates a skeleton internal FAQ pre-filled with "
                 "documentation about OpenERP's Document Management "
                 "System."),
        'wiki_quality_manual':fields.boolean('Template: Quality Manual',
            help="Creates an example skeleton for a standard quality manual."),
        }
    _defaults = {
        'document_ftp':True,
        }

knowledge_installer()
