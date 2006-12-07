##############################################################################
#
# Copyright (c) 2004 TINY SPRL. (http://tiny.be) All Rights Reserved.
#                    Fabien Pinckaers <fp@tiny.Be>
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

# trml2pdf - An RML to PDF converter
# Copyright (C) 2003, Fabien Pinckaers, UCL, FSA
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import re
import reportlab

def text_get(node):
	rc = ''
	for node in node.childNodes:
		if node.nodeType == node.TEXT_NODE:
			rc = rc + node.data
	return rc

units = [
	(re.compile('^(-?[0-9\.]+)\s*in$'), reportlab.lib.units.inch),
	(re.compile('^(-?[0-9\.]+)\s*cm$'), reportlab.lib.units.cm),  
	(re.compile('^(-?[0-9\.]+)\s*mm$'), reportlab.lib.units.mm),
	(re.compile('^(-?[0-9\.]+)\s*$'), 1)
]

def unit_get(size):
	global units
	for unit in units:
		res = unit[0].search(size, 0)
		if res:
			return unit[1]*float(res.group(1))
	return False

def tuple_int_get(node, attr_name, default=None):
	if not node.hasAttribute(attr_name):
		return default
	res = [int(x) for x in node.getAttribute(attr_name).split(',')]
	return res

def bool_get(value):
	return (str(value)=="1") or (value.lower()=='yes')

def attr_get(node, attrs, dict={}):
	res = {}
	for name in attrs:
		if node.hasAttribute(name):
			res[name] =  unit_get(node.getAttribute(name))
	for key in dict:
		if node.hasAttribute(key):
			if dict[key]=='str':
				res[key] = str(node.getAttribute(key))
			elif dict[key]=='bool':
				res[key] = bool_get(node.getAttribute(key))
			elif dict[key]=='int':
				res[key] = int(node.getAttribute(key))
	return res
