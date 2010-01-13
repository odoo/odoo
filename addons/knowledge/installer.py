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
    _name = 'knowledge.installer'
    _inherit = 'res.config.installer'

    _columns = {
        # Knowledge Management
        'document_ftp':fields.boolean('Shared Repositories (FTP)'),
        'document_webdav':fields.boolean('Shared Repositories (WebDAV)'),
        'wiki':fields.boolean('Collaborative Content (Wiki)'),
        # Templates of Content
        'wiki_faq':fields.boolean('Internal FAQ'),
        'wiki_quality_manual':fields.boolean('Quality Manual'),
        }
    _defaults = {
        'document_ftp':True,
        }

knowledge_installer()
