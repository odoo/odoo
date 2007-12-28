##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
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


import xml.dom.minidom
import os, time
import ir, netsvc
import osv
from interface import  report_rml
import re
import tools
import pooler
import netsvc
import warnings
import locale
import copy
import StringIO
import zipfile

DT_FORMAT = '%Y-%m-%d'
DHM_FORMAT = '%Y-%m-%d %H:%M:%S'
HM_FORMAT = '%H:%M:%S'

if not hasattr(locale, 'nl_langinfo'):
	locale.nl_langinfo = lambda *a: '%x'

if not hasattr(locale, 'D_FMT'):
	locale.D_FMT = None

rml_parents = {
	'tr':1,
	'li':1,
	'story': 0,
	'section': 0
}

rml_tag="para"

sxw_parents = {
	'table-row': 1,
	'list-item': 1,
	'body': 0,
	'section': 0,
}

sxw_tag = "p"

rml2sxw = {
	'para': 'p',
}

#
# Context: {'node': node.dom}
#
class browse_record_list(list):
	def __init__(self, lst, context):
		super(browse_record_list, self).__init__(lst)
		self.context = context

	def __getattr__(self, name):
		res = browse_record_list([getattr(x,name) for x in self], self.context)
		return res

	def __str__(self):
		return "browse_record_list("+str(len(self))+")"

	def repeatIn(self, name):
		warnings.warn('Use repeatIn(object_list, \'variable\')', DeprecationWarning)
		node = self.context['_node']
		parents = self.context.get('parents', rml_parents)
		node.data = ''
		while True:
			if not node.parentNode:
				break
			node = node.parentNode
			if node.nodeType == node.ELEMENT_NODE and node.localName in parents:
				break
		parent_node = node
		if not len(self):
			return None
		nodes = [(0,node)]
		for i in range(1,len(self)):
			newnode = parent_node.cloneNode(1)
			n = parent_node.parentNode
			n.insertBefore(newnode, parent_node)
			nodes.append((i,newnode))
		for i,node in nodes:
			self.context[name] = self[i]
			self.context['_self']._parse_node(node)
		return None

class rml_parse(object):
	def __init__(self, cr, uid, name, parents=rml_parents, tag=rml_tag, context=None):
		if not context:
			context={}
		self.cr = cr
		self.uid = uid
		self.pool = pooler.get_pool(cr.dbname)
		user = self.pool.get('res.users').browse(cr, uid, uid)
		self.localcontext = {
			'user': user,
			'company': user.company_id,
			'repeatIn': self.repeatIn,
			'setLang': self.setLang,
			'setTag': self.setTag,
			'removeParentNode': self.removeParentNode,
			'format': self.format,
			'formatLang': self.formatLang,
		}
		self.localcontext.update(context)
		self.name = name
		self._regex = re.compile('\[\[(.+?)\]\]')
		self._transl_regex = re.compile('(\[\[.+?\]\])')
		self._node = None
		self.parents = parents
		self.tag = tag
#		self.already = {}

	def setTag(self, oldtag, newtag, attrs=None):
		if not attrs:
			attrs={}
		node = self._find_parent(self._node, [oldtag])
		if node:
			node.tagName = newtag
			for key, val in attrs.items():
				node.setAttribute(key, val)
		return None

	def format(self, text, oldtag=None):
		if not oldtag:
			oldtag = self.tag
		self._node.data = ''
		node = self._find_parent(self._node, [oldtag])

		pp = node.parentNode
		ns = node.nextSibling
		pp.removeChild(node)
		self._node = pp
		lst = text.split('\n')
		if not len(lst):
			return None
		nodes = []
		for i in range(len(lst)):
			newnode = node.cloneNode(1)
			newnode.tagName=rml_tag
			newnode.__dict__['childNodes'][0].__dict__['data'] = lst[i].decode('utf8')
			if ns:
				pp.insertBefore(newnode, ns)
			else:
				pp.appendChild(newnode)
			nodes.append((i, newnode))

	def removeParentNode(self, tag=None):
		if not tag:
			tag = self.tag
		if self.tag == sxw_tag and rml2sxw.get(tag, False):
			tag = rml2sxw[tag]
		node = self._find_parent(self._node, [tag])
		if node:
			parentNode = node.parentNode
			parentNode.removeChild(node)
			self._node = parentNode

	def setLang(self, lang):
		self.localcontext['lang'] = lang

	def formatLang(self, value, digit=2, date=False):
		lc, encoding = locale.getdefaultlocale()
		if encoding == 'utf':
			encoding = 'UTF-8'
		try:
			locale.setlocale(locale.LC_ALL,
					(self.localcontext.get('lang', 'en_US') or 'en_US') + \
							'.' + encoding)
		except Exception:
			netsvc.Logger().notifyChannel('report', netsvc.LOG_WARNING,
					'report %s: unable to set locale "%s"' % (self.name,
						self.localcontext.get('lang', 'en_US') or 'en_US'))
		if date:
			date = time.strptime(value, DT_FORMAT)
			return time.strftime(locale.nl_langinfo(locale.D_FMT).replace('%y', '%Y'),
					date)
		return locale.format('%.' + str(digit) + 'f', value, True)

	def repeatIn(self, lst, name, nodes_parent=False):
		self._node.data = ''
		node = self._find_parent(self._node, nodes_parent or self.parents)

		pp = node.parentNode
		ns = node.nextSibling
		pp.removeChild(node)
		self._node = pp

		if not len(lst):
			return None
		nodes = []
		for i in range(len(lst)):
			newnode = node.cloneNode(1)
			if ns:
				pp.insertBefore(newnode, ns)
			else:
				pp.appendChild(newnode)
			nodes.append((i, newnode))
		for i, node in nodes:
			self.node_context[node] = {name: lst[i]}
		return None

	def _eval(self, expr):
		try:
			res = eval(expr, self.localcontext)
			if not res:
				res = ''
		except Exception,e:
			import traceback, sys
			tb_s = reduce(lambda x, y: x+y, traceback.format_exception(sys.exc_type, sys.exc_value, sys.exc_traceback))
			netsvc.Logger().notifyChannel('report', netsvc.LOG_ERROR,
					'report %s:\n%s\n%s\nexpr: %s' % (self.name, tb_s, str(e),
						expr.encode('utf-8')))
			res = ''
		return res

	def _find_parent(self, node, parents):
		while True:
			if not node.parentNode:
				return False
			node = node.parentNode
			if node.nodeType == node.ELEMENT_NODE and node.localName in parents:
				break
		return node

	def _parse_text(self, text, level=None):
		if not level:
			level=[]
		res = self._regex.findall(text)
		todo = []
		# translate the text
		# the "split [[]] if not match [[]]" is not very nice, but I 
		# don't see how I could do it better...
		# what I'd like to do is a re.sub(NOT pattern, func, string)
		# but I don't know how to do that...
		# translate the RML file
		if 'lang' in self.localcontext:
			lang = self.localcontext['lang']
			if lang and text and not text.isspace():
				transl_obj = self.pool.get('ir.translation')
				piece_list = self._transl_regex.split(text)
				for pn in range(len(piece_list)):
					if not self._transl_regex.match(piece_list[pn]):
						source_string = piece_list[pn].replace('\n', ' ').strip()
						if len(source_string):
							translated_string = transl_obj._get_source(self.cr, self.uid, self.name, 'rml', lang, source_string)
							if translated_string:
								piece_list[pn] = piece_list[pn].replace(source_string, translated_string.decode('utf8'))
				text = ''.join(piece_list)
		for key in res:
			newtext = self._eval(key)
			for i in range(len(level)):
				if isinstance(newtext, list):
					newtext = newtext[level[i]]
			if isinstance(newtext, list):
				todo.append((key, newtext))
			else:
				if not isinstance(newtext, basestring):
					newtext = str(newtext)
				# if there are two [[]] blocks the same, it will replace both
				# but it's ok because it should evaluate to the same thing 
				# anyway
				text = text.replace('[['+key+']]', newtext.decode('utf8'))
		self._node.data = text
		if len(todo):
			for key, newtext in todo:
				parent_node = self._find_parent(self._node, parents)
				assert parents.get(parent_node.localName, False), 'No parent node found !'
				nodes = [parent_node]
				for i in range(len(newtext) - 1):
					newnode = parent_node.cloneNode(1)
					if parents.get(parent_node.localName, False):
						n = parent_node.parentNode
						parent_node.parentNode.insertAfter(newnode, parent_node)
						nodes.append(newnode)
			return False
		return text

	def _parse_node(self):
		level = []
		while True:
			if self._node.nodeType==self._node.ELEMENT_NODE:
				if self._node.hasAttribute('expr'):
					newattrs = self._eval(self._node.getAttribute('expr'))
					for key,val in newattrs.items():
						self._node.setAttribute(key,val)

			if self._node.hasChildNodes():
				self._node = self._node.firstChild
			elif self._node.nextSibling:
				self._node = self._node.nextSibling
			else:
				while self._node and not self._node.nextSibling:
					self._node = self._node.parentNode
				if not self._node:
					break
				self._node = self._node.nextSibling
			if self._node in self.node_context:
				self.localcontext.update(self.node_context[self._node])
			if self._node.nodeType in (self._node.CDATA_SECTION_NODE, self._node.TEXT_NODE):
#				if self._node in self.already:
#					self.already[self._node] += 1 
#					print "second pass!", self.already[self._node], '---%s---' % self._node.data
#				else:
#					self.already[self._node] = 0
				self._parse_text(self._node.data, level)
		return True

	def _find_node(self, node, localname):
		if node.localName==localname:
			return node
		for tag in node.childNodes:
			if tag.nodeType==tag.ELEMENT_NODE:
				found = self._find_node(tag, localname)
				if found:
					return found
		return False

	def _add_header(self, node):
		rml_head = tools.file_open('custom/corporate_rml_header.rml').read()
		head_dom = xml.dom.minidom.parseString(rml_head)
		#for frame in head_dom.getElementsByTagName('frame'):
		#	frame.parentNode.removeChild(frame)
		node2 = head_dom.documentElement
		for tag in node2.childNodes:
			if tag.nodeType==tag.ELEMENT_NODE:
				found = self._find_node(node, tag.localName)
		#		rml_frames = found.getElementsByTagName('frame')
				if found:
					if tag.hasAttribute('position') and (tag.getAttribute('position')=='inside'):
						found.appendChild(tag)
					else:
						found.parentNode.replaceChild(tag, found)
		#		for frame in rml_frames:
		#			tag.appendChild(frame)
		return True

	def preprocess(self, objects, data, ids):
		self.localcontext['data'] = data
		self.localcontext['objects'] = objects
		self.datas = data
		self.ids = ids
		self.objects = objects

	def _parse(self, rml_dom, objects, data, header=False):
		self.node_context = {}
		self.dom = rml_dom
		self._node = self.dom.documentElement
		if header:
			self._add_header(self._node)
		self._parse_node()
		res = self.dom.documentElement.toxml('utf-8')
		return res

class report_sxw(report_rml):
	def __init__(self, name, table, rml, parser=rml_parse, header=True):
		report_rml.__init__(self, name, table, rml, '')
		self.name = name
		self.parser = parser
		self.header = header

	def getObjects(self, cr, uid, ids, context):
		table_obj = pooler.get_pool(cr.dbname).get(self.table)
		return table_obj.browse(cr, uid, ids, list_class=browse_record_list, context=context)

	def create(self, cr, uid, ids, data, context=None):
		if not context:
			context={}
		context = context.copy()
		pool = pooler.get_pool(cr.dbname)
		ir_actions_report_xml_obj = pool.get('ir.actions.report.xml')
		report_xml_ids = ir_actions_report_xml_obj.search(cr, uid,
				[('report_name', '=', self.name[7:])], context=context)
		report_type = 'pdf'
		report_xml = None
		if report_xml_ids:
			report_xml = ir_actions_report_xml_obj.browse(cr, uid, report_xml_ids[0],
					context=context)
			rml = report_xml.report_rml_content
			report_type = report_xml.report_type
		else:
			rml = tools.file_open(self.tmpl, subdir=None).read()
		report_type= data.get('report_type', report_type)

		if report_type == 'sxw' and report_xml:
			context['parents'] = sxw_parents
			sxw_io = StringIO.StringIO(report_xml.report_sxw_content)
			sxw_z = zipfile.ZipFile(sxw_io, mode='r')
			rml = sxw_z.read('content.xml')
			meta = sxw_z.read('meta.xml')
			sxw_z.close()
			rml_parser = self.parser(cr, uid, self.name2, context)
			rml_parser.parents = sxw_parents
			rml_parser.tag = sxw_tag
			objs = self.getObjects(cr, uid, ids, context)
			rml_parser.preprocess(objs, data, ids)
			rml_dom = xml.dom.minidom.parseString(rml)

			node = rml_dom.documentElement
			elements = node.getElementsByTagName("text:p")
			for pe in elements:
				e = pe.getElementsByTagName("text:drop-down")
				for de in e:
					for cnd in de.childNodes:
						if cnd.nodeType in (cnd.CDATA_SECTION_NODE, cnd.TEXT_NODE):
							pe.appendChild(cnd)
							pe.removeChild(de)

			rml2 = rml_parser._parse(rml_dom, objs, data, header=self.header)
			sxw_z = zipfile.ZipFile(sxw_io, mode='a')
			sxw_z.writestr('content.xml', "<?xml version='1.0' encoding='UTF-8'?>" + \
					rml2)
			if self.header:
				#Add corporate header/footer
				rml = tools.file_open('custom/corporate_sxw_header.xml').read()
				rml_parser = self.parser(cr, uid, self.name2, context)
				rml_parser.parents = sxw_parents
				rml_parser.tag = sxw_tag
				objs = self.getObjects(cr, uid, ids, context)
				rml_parser.preprocess(objs, data, ids)
				rml_dom = xml.dom.minidom.parseString(rml)
				rml2 = rml_parser._parse(rml_dom, objs, data, header=self.header)
				sxw_z.writestr('styles.xml',"<?xml version='1.0' encoding='UTF-8'?>" + \
						rml2)
			sxw_z.close()
			rml2 = sxw_io.getvalue()
			sxw_io.close()
		else:
			context['parents'] = rml_parents
			rml_parser = self.parser(cr, uid, self.name2, context)
			rml_parser.parents = rml_parents
			rml_parser.tag = rml_tag
			objs = self.getObjects(cr, uid, ids, context)
			rml_parser.preprocess(objs, data, ids)
			rml_dom = xml.dom.minidom.parseString(rml)
			rml2 = rml_parser._parse(rml_dom, objs, data, header=self.header)
			#if os.name != "nt":
			#	f = file("/tmp/debug.rml", "w")
			#	f.write(rml2)
			#	f.close()
		create_doc = self.generators[report_type]
		pdf = create_doc(rml2)
		return (pdf, report_type)


