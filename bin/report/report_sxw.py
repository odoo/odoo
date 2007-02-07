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

import copy

parents = {
	'tr':1,
	'li':1,
	'story': 0,
	'section': 0
}

#
# Context: {'node': node.dom}
#
class browse_record_list(list):
	def __init__(self, lst, context):
		super(browse_record_list, self).__init__(lst)
		self.parents = copy.copy(parents)
		self.context = context

	def __getattr__(self, name):
		res = browse_record_list([getattr(x,name) for x in self], self.context)
		return res

	def __str__(self):
		return "browse_record_list("+str(len(self))+")"

	def repeatIn(self, name):
		print 'Decrecated ! Use repeatIn(object_list, \'variable\')'
		node = self.context['_node']
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
	def __init__(self, cr, uid, name, context={}):
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
		}
		self.localcontext.update(context)
		self.name = name
		self._regex = re.compile('\[\[(.+?)\]\]')
		self._transl_regex = re.compile('(\[\[.+?\]\])')
		self._node = None
#		self.already = {}
	
	def setTag(self, oldtag, newtag, attrs={}):
		node = self._find_parent(self._node, [oldtag])
		if node:
			node.tagName = newtag
			for key, val in attrs.items():
				node.setAttribute(key, val)
		return None

	def removeParentNode(self, tag):
		node = self._find_parent(self._node, [tag])
		if node:
			parentNode = node.parentNode
			parentNode.removeChild(node)
			self._node = parentNode

	def setLang(self, lang):
		self.localcontext['lang'] = lang

	def repeatIn(self, lst, name, nodes_parent=False):
		self._node.data = ''
		node = self._find_parent(self._node, nodes_parent or parents)

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
			if res is False or res is None:
				res = ''
		except Exception,e:
			res = 'Error'
		return res

	def _find_parent(self, node, parents):
		while True:
			if not node.parentNode:
				return False
			node = node.parentNode
			if node.nodeType == node.ELEMENT_NODE and node.localName in parents:
				break
		return node

	def _parse_text(self, text, level=[]):
		res = self._regex.findall(text)
		todo = []
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
		# translate the text
		# the "split [[]] if not match [[]]" is not very nice, but I 
		# don't see how I could do it better...
		# what I'd like to do is a re.sub(NOT pattern, func, string)
		# but I don't know how to do that...
		# translate the RML file
		if 'lang' in self.localcontext:
			lang = self.localcontext['lang']
			if lang not in (False, 'en') and text and not text.isspace():
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

	def create(self, cr, uid, ids, data, context={}):
		rml = file(os.path.join(tools.config['root_path'], self.tmpl)).read()

		rml_parser = self.parser(cr, uid, self.name2, context)
		objs = self.getObjects(cr, uid, ids, context)
		rml_parser.preprocess(objs, data, ids)
		
		rml_dom = xml.dom.minidom.parseString(rml)
		
		rml2 = rml_parser._parse(rml_dom, objs, data, header=self.header)
		#import os
		#if os.name != "nt":
		#	f = file("/tmp/debug.rml", "w")
		#	f.write(rml2)
		#	f.close()
		report_type= data.get('report_type','pdf')
		create_doc = self.generators[report_type]
		pdf = create_doc(rml2)
		return (pdf, report_type)


