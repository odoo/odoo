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

import copy
import locale

import logging
import re
import reportlab

import openerp.tools as tools
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.misc import ustr

_regex = re.compile('\[\[(.+?)\]\]')

def str2xml(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def xml2str(s):
    return (s or '').replace('&amp;','&').replace('&lt;','<').replace('&gt;','>')

def _child_get(node, self=None, tagname=None):
    for n in node:
        if self and self.localcontext and n.get('rml_loop'):

            for ctx in eval(n.get('rml_loop'),{}, self.localcontext):
                self.localcontext.update(ctx)
                if (tagname is None) or (n.tag==tagname):
                    if n.get('rml_except', False):
                        try:
                            eval(n.get('rml_except'), {}, self.localcontext)
                        except GeneratorExit:
                            continue
                        except Exception, e:
                            logging.getLogger('report').warning('rml_except: "%s"',n.get('rml_except',''), exc_info=True)
                            continue
                    if n.get('rml_tag'):
                        try:
                            (tag,attr) = eval(n.get('rml_tag'),{}, self.localcontext)
                            n2 = copy.deepcopy(n)
                            n2.tag = tag
                            n2.attrib.update(attr)
                            yield n2
                        except GeneratorExit:
                            yield n
                        except Exception, e:
                            logging.getLogger('report').warning('rml_tag: "%s"',n.get('rml_tag',''), exc_info=True)
                            yield n
                    else:
                        yield n
            continue
        if self and self.localcontext and n.get('rml_except'):
            try:
                eval(n.get('rml_except'), {}, self.localcontext)
            except GeneratorExit:
                continue
            except Exception, e:
                logging.getLogger('report').warning('rml_except: "%s"',n.get('rml_except',''), exc_info=True)
                continue
        if self and self.localcontext and n.get('rml_tag'):
            try:
                (tag,attr) = eval(n.get('rml_tag'),{}, self.localcontext)
                n2 = copy.deepcopy(n)
                n2.tag = tag
                n2.attrib.update(attr or {})
                yield n2
                tagname = ''
            except GeneratorExit:
                pass
            except Exception, e:
                logging.getLogger('report').warning('rml_tag: "%s"',n.get('rml_tag',''), exc_info=True)
                pass
        if (tagname is None) or (n.tag==tagname):
            yield n

def _process_text(self, txt):
        '''
        Translate a text and escape it for xml.

        :param txt: text, varchar to process
        :return: translated and escaped text
        '''
        if not self.localcontext:
            return str2xml(txt)
        if not txt:
            return ''
        result = ''
        sps = _regex.split(txt)
        while sps:
            # This is a simple text to translate
            to_translate = tools.ustr(sps.pop(0))
            result += tools.ustr(self.localcontext.get('translate', lambda x:x)(to_translate))
            if sps:
                try:
                    txt = None
                    expr = sps.pop(0)
                    txt = eval(expr, self.localcontext)
                    if txt and isinstance(txt, basestring):
                        txt = tools.ustr(txt)
                except Exception:
                    pass
                if isinstance(txt, basestring):
                    result += txt
                elif txt and (txt is not None) and (txt is not False):
                    result += ustr(txt)
        return str2xml(result)

def text_get(node):
    return ''.join([ustr(n.text) for n in node])

units = [
    (re.compile('^(-?[0-9\.]+)\s*in$'), reportlab.lib.units.inch),
    (re.compile('^(-?[0-9\.]+)\s*cm$'), reportlab.lib.units.cm),
    (re.compile('^(-?[0-9\.]+)\s*mm$'), reportlab.lib.units.mm),
    (re.compile('^(-?[0-9\.]+)\s*$'), 1)
]

def unit_get(size):
    global units
    if size:
        if size.find('.') == -1:
            decimal_point = '.'
            try:
                decimal_point = locale.nl_langinfo(locale.RADIXCHAR)
            except Exception:
                decimal_point = locale.localeconv()['decimal_point']

            size = size.replace(decimal_point, '.')

        for unit in units:
            res = unit[0].search(size, 0)
            if res:
                return unit[1]*float(res.group(1))
    return False

def tuple_int_get(node, attr_name, default=None):
    if not node.get(attr_name):
        return default
    return map(int, node.get(attr_name).split(','))

def bool_get(value):
    return (str(value)=="1") or (value.lower()=='yes')

def attr_get(node, attrs, dict={}):
    res = {}
    for name in attrs:
        if node.get(name):
            res[name] = unit_get(node.get(name))
    for key in dict:
        if node.get(key):
            if dict[key]=='str':
                res[key] = tools.ustr(node.get(key))
            elif dict[key]=='bool':
                res[key] = bool_get(node.get(key))
            elif dict[key]=='int':
                res[key] = int(node.get(key))
            elif dict[key]=='unit':
                res[key] = unit_get(node.get(key))
            elif dict[key] == 'float' :
                res[key] = float(node.get(key))
    return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
