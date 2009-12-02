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
import base64

from osv import osv, fields
from osv.orm import except_orm
import urlparse

import os
import nodes

class document_directory_content_type(osv.osv):
    _name = 'document.directory.content.type'
    _description = 'Directory Content Type'
    _columns = {
        'name': fields.char('Content Type', size=64, required=True),
        'code': fields.char('Extension', size=4),
        'active': fields.boolean('Active'),
        'mimetype': fields.char('Mime Type',size=32)
    }
    _defaults = {
        'active': lambda *args: 1
    }
document_directory_content_type()

class document_directory_content(osv.osv):
    _name = 'document.directory.content'
    _description = 'Directory Content'
    _order = "sequence"
    def _extension_get(self, cr, uid, context={}):
        cr.execute('select code,name from document_directory_content_type where active')
        res = cr.fetchall()
        return res
    _columns = {
        'name': fields.char('Content Name', size=64, required=True),
        'sequence': fields.integer('Sequence', size=16),
        'prefix': fields.char('Prefix', size=16),
        'suffix': fields.char('Suffix', size=16),
        'report_id': fields.many2one('ir.actions.report.xml', 'Report'),
        'extension': fields.selection(_extension_get, 'Document Type', required=True, size=4),
        'include_name': fields.boolean('Include Record Name', help="Check this field if you want that the name of the file start by the record name."),
        'directory_id': fields.many2one('document.directory', 'Directory'),
    }
    _defaults = {
        'extension': lambda *args: '.pdf',
        'sequence': lambda *args: 1,
        'include_name': lambda *args: 1,
    }
    
    def _file_get(self,cr,node, nodename, content, context=None):
	""" return the nodes of a <node> parent having a <content> content
	    The return value MUST be false or a list of node_class objects.
	"""
	
	# TODO: respect the context!
	if content.include_name and not node.object2:
		return False
	
	res2 = []
	tname = ''
	if content.include_name:
		content_name = node.object2.name
		obj = pool.get(node.object.ressource_type_id.model)
		name_for = obj._name.split('.')[-1]
		if content_name  and content_name.find(name_for) == 0  :
			content_name = content_name.replace(name_for,'')
			tname = (content.prefix or '') + content_name + (content.suffix or '') + (content.extension or '')
	else:
		tname = (content.prefix or '') + (content.suffix or '') + (content.extension or '')
	if tname.find('/'):
		tname=tname.replace('/', '_')
	if not nodename:
		n = nodes.node_content(tname, node, node.context,content)
		res2.append( n)
	else:
		if nodename == tname:
			n = nodes.node_content(tname, node, node.context,content)
			n.fill_fields(cr)
			res2.append(n)
	return res2

    def process_write(self, cr, uid, node, data):
	if node.extension != '.pdf':
		raise Exception("Invalid content: %s" % node.extension)
        return True
    def process_read(self, cr, uid, node):
	if node.extension != '.pdf':
		raise Exception("Invalid content: %s" % node.extension)
        report = self.pool.get('ir.actions.report.xml').browse(cr, uid, node.content.report_id.id)
        srv = netsvc.LocalService('report.'+report.report_name)
        pdf,pdftype = srv.create(cr, uid, [node.object.id], {}, {})
        s = StringIO.StringIO(pdf)
        s.name = node
        return s
document_directory_content()
