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

import copy
import re
import reportlab
import reportlab.lib.units
from lxml import etree
from openerp.tools.safe_eval import safe_eval as eval

_regex = re.compile('\[\[(.+?)\]\]')

def _child_get(node, self=None, tagname=None):
    for n in node:
        if self and self.localcontext and n.get('rml_loop', False):
            oldctx = self.localcontext
            for ctx in eval(n.get('rml_loop'),{}, self.localcontext):
                self.localcontext.update(ctx)
                if (tagname is None) or (n.tag==tagname):
                    if n.get('rml_except', False):
                        try:
                            eval(n.get('rml_except'), {}, self.localcontext)
                        except:
                            continue
                    if n.get('rml_tag'):
                        try:
                            (tag,attr) = eval(n.get('rml_tag'),{}, self.localcontext)
                            n2 = copy.copy(n)
                            n2.tag = tag
                            n2.attrib.update(attr)
                            yield n2
                        except:
                            yield n
                    else:
                        yield n
            self.localcontext = oldctx
            continue
        if self and self.localcontext and n.get('rml_except', False):
            try:
                eval(n.get('rml_except'), {}, self.localcontext)
            except:
                continue
        if (tagname is None) or (n.tag==tagname):
            yield n

def _process_text(self, txt):
        if not self.localcontext:
            return txt
        if not txt:
            return ''
        result = ''
        sps = _regex.split(txt)
        while sps:
            # This is a simple text to translate
            result += self.localcontext.get('translate', lambda x:x)(sps.pop(0))
            if sps:
                try:
                    txt2 = eval(sps.pop(0),self.localcontext)
                except:
                    txt2 = ''
                if type(txt2) == type(0) or type(txt2) == type(0.0):
                    txt2 = str(txt2)
                if type(txt2)==type('') or type(txt2)==type(u''):
                    result += txt2
        return result

def text_get(node):
    rc = ''
    for node in node.getchildren():
            rc = rc + node.text
    return rc

units = [
    (re.compile('^(-?[0-9\.]+)\s*in$'), reportlab.lib.units.inch),
    (re.compile('^(-?[0-9\.]+)\s*cm$'), reportlab.lib.units.cm),
    (re.compile('^(-?[0-9\.]+)\s*mm$'), reportlab.lib.units.mm),
    (re.compile('^(-?[0-9\.]+)\s*$'), 1)
]

def unit_get(size):
    global units
    if size:
        for unit in units:
            res = unit[0].search(size, 0)
            if res:
                return unit[1]*float(res.group(1))
    return False

def tuple_int_get(node, attr_name, default=None):
    if not node.get(attr_name):
        return default
    res = [int(x) for x in node.get(attr_name).split(',')]
    return res

def bool_get(value):
    return (str(value)=="1") or (value.lower()=='yes')

def attr_get(node, attrs, dict=None):
    if dict is None:
        dict = {}
    res = {}
    for name in attrs:
        if node.get(name):
            res[name] = unit_get(node.get(name))
    for key in dict:
        if node.get(key):
            if dict[key]=='str':
                res[key] = str(node.get(key))
            elif dict[key]=='bool':
                res[key] = bool_get(node.get(key))
            elif dict[key]=='int':
                res[key] = int(node.get(key))
            elif dict[key]=='unit':
                res[key] = unit_get(node.get(key))
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
