##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# $Id: interface.py 1304 2005-09-08 14:35:42Z nicoe $
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import os,re

#Ged> Why do we use libxml2 here instead of xml.dom like in other places of the code?
import libxml2
import libxslt

import netsvc
import pooler

import tools
import print_xml
import render

#
# encode a value to a string in utf8 and converts XML entities
#
def toxml(val):
	if isinstance(val, str):
		str_utf8 = val
	elif isinstance(val, unicode):
		str_utf8 = val.encode('utf-8')
	else:
		str_utf8 = str(val)
	return str_utf8.replace('&', '&amp;').replace('<','&lt;').replace('>','&gt;')

class report_int(netsvc.Service):
	def __init__(self, name, audience='*'):
		assert not netsvc.service_exist(name), 'The report "%s" already exist!'%name
		super(report_int, self).__init__(name, audience)
		if name[0:7]<>'report.':
			raise Exception, 'ConceptionError, bad report name, should start with "report."'
		self.name = name
		self.id = 0
		self.name2 = '.'.join(name.split('.')[1:])
		self.joinGroup('report')
		self.exportMethod(self.create)

	def create(self, cr, uid, ids, datas, context=None):
		return False

"""
	Class to automatically build a document using the transformation process:
		XML -> DATAS -> RML -> PDF
		                    -> HTML
	using a XSL:RML transformation
"""
class report_rml(report_int):
	def __init__(self, name, table, tmpl, xsl):
		super(report_rml, self).__init__(name)
		self.table = table
		self.tmpl = tmpl
		self.xsl = xsl
		self.bin_datas = {}
		self.generators = {'pdf': self.create_pdf, 'html': self.create_html, 'raw': self.create_raw}

	def create(self, cr, uid, ids, datas, context):
		xml = self.create_xml(cr, uid, ids, datas, context)
#		file('/tmp/terp.xml','wb+').write(xml)
		if datas.get('report_type', 'pdf') == 'raw':
			return xml
		rml = self.create_rml(cr, xml, uid, context)
#		file('/tmp/terp.rml','wb+').write(rml)
		report_type = datas.get('report_type', 'pdf')
		create_doc = self.generators[report_type]
		pdf = create_doc(rml)
		return (pdf, report_type)
	
	def create_xml(self, cr, uid, ids, datas, context=None):
		if not context:
			context={}
		doc = print_xml.document(cr, uid, datas, {})
		self.bin_datas = doc.bin_datas
		doc.parse(self.tmpl, ids, self.table, context)
		xml = doc.xml_get()
		doc.close()
		return self.post_process_xml_data(cr, uid, xml, context)

	def post_process_xml_data(self, cr, uid, xml, context=None):
		if not context:
			context={}
		# find the position of the 3rd tag 
		# (skip the <?xml ...?> and the "root" tag)
		iter = re.finditer('<[^>]*>', xml)
		i = iter.next()
		i = iter.next()
		pos_xml = i.end()

		doc = print_xml.document(cr, uid, {}, {})
		tmpl_path = os.path.join(tools.config['root_path'], 'addons/custom/corporate_defaults.xml')
		doc.parse(tmpl_path, [uid], 'res.users', context)
		corporate_header = doc.xml_get()
		doc.close()

		# find the position of the tag after the <?xml ...?> tag
		iter = re.finditer('<[^>]*>', corporate_header)
		i = iter.next()
		pos_header = i.end()

		return xml[:pos_xml] + corporate_header[pos_header:] + xml[pos_xml:]

	#
	# TODO: The translation doesn't work for "<tag t="1">textext<tag> tex</tag>text</tag>"
	#
	def create_rml(self, cr, xml, uid, context=None):
		if not context:
			context={}
		service = netsvc.LocalService("object_proxy")

		# In some case we might not use xsl ...
		if not self.xsl:
			return xml

		# load XSL (parse it to the XML level)
		styledoc = libxml2.parseFile(os.path.join(tools.config['root_path'],self.xsl))
		
		#TODO: get all the translation in one query. That means we have to: 
		# * build a list of items to translate, 
		# * issue the query to translate them,
		# * (re)build/update the stylesheet with the translated items

		# translate the XSL stylesheet
		def look_down(child, lang):
			while child is not None:
				if (child.type == "element") and child.hasProp('t'):
					#FIXME: use cursor
					res = service.execute(cr.dbname, uid, 'ir.translation', '_get_source', self.name2, 'xsl', lang, child.content)
					if res:
						child.setContent(res)
				look_down(child.children, lang)
				child = child.next

		if context.get('lang', False):
			look_down(styledoc.children, context['lang'])

		style = libxslt.parseStylesheetDoc(styledoc)			# parse XSL

		doc = libxml2.parseMemory(xml,len(xml))					# load XML (data)
		result = style.applyStylesheet(doc, None)				# create RML (apply XSL to XML data)
		xml = style.saveResultToString(result)					# save result to string
		
		style.freeStylesheet()
		doc.freeDoc()
		result.freeDoc()
		return xml
	
	def create_pdf(self, xml):
		obj = render.rml(xml, self.bin_datas, os.path.dirname(self.tmpl))
		obj.render()
		return obj.get()

	def create_html(self, xml):
		obj = render.rml2html(xml, self.bin_datas)
		obj.render()
		return obj.get()

	def create_raw(self, xml):
		return xml

from report_sxw import report_sxw

def register_all(db):
	opj = os.path.join
	#FIXME: multi-db, quoique... ca init le code donc ok. Enfin, du moins si les modules sont les memes.
	cr = db.cursor()
	cr.execute("SELECT * FROM ir_act_report_xml WHERE auto ORDER BY id")
	result = cr.dictfetchall()
	cr.close()
	for r in result:
		if netsvc.service_exist('report.'+r['report_name']):
			continue
		if r['report_rml']:
			report_sxw('report.'+r['report_name'], r['model'], opj('addons',r['report_rml']), header=r['header'])
		if r['report_xsl']:
			report_rml('report.'+r['report_name'], r['model'], opj('addons',r['report_xml']), r['report_xsl'] and opj('addons',r['report_xsl']))

