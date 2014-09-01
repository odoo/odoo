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

from lxml import etree
import openerp
import openerp.tools as tools
from openerp.tools.safe_eval import safe_eval
import print_fnc
from openerp.osv.orm import BaseModel

class InheritDict(dict):
    # Might be usefull when we're doing name lookup for call or eval.

    def __init__(self, parent=None):
        self.parent = parent

    def __getitem__(self, name):
        if name in self:
            return super(InheritDict, self).__getitem__(name)
        else:
            if not self.parent:
                raise KeyError
            else:
                return self.parent[name]

def tounicode(val):
    if isinstance(val, str):
        unicode_val = unicode(val, 'utf-8')
    elif isinstance(val, unicode):
        unicode_val = val
    else:
        unicode_val = unicode(val)
    return unicode_val

class document(object):
    def __init__(self, cr, uid, datas, func=False):
        # create a new document
        self.cr = cr
        self.pool = openerp.registry(cr.dbname)
        self.func = func or {}
        self.datas = datas
        self.uid = uid
        self.bin_datas = {}

    def node_attrs_get(self, node):
        if len(node.attrib):
            return node.attrib
        return {}

    def get_value(self, browser, field_path):
        fields = field_path.split('.')

        if not len(fields):
            return ''

        value = browser

        for f in fields:
            if isinstance(value, (BaseModel, list)):
                if not value:
                    return ''
                value = value[0]
            value = value[f]

        return value or ''

    def get_value2(self, browser, field_path):
        value = self.get_value(browser, field_path)
        if isinstance(value, BaseModel):
            return value.id
        else:
            return value

    def eval(self, record, expr):
#TODO: support remote variables (eg address.title) in expr
# how to do that: parse the string, find dots, replace those dotted variables by temporary
# "simple ones", fetch the value of those variables and add them (temporarily) to the _data
# dictionary passed to eval

#FIXME: it wont work if the data hasn't been fetched yet... this could
# happen if the eval node is the first one using this Record
# the next line is a workaround for the problem: it causes the resource to be loaded
#Pinky: Why not this ? eval(expr, browser) ?
#       name = browser.name
#       data_dict = browser._data[self.get_value(browser, 'id')]
        return safe_eval(expr, {}, {'obj': record})

    def parse_node(self, node, parent, browser, datas=None):
            attrs = self.node_attrs_get(node)
            if 'type' in attrs:
                if attrs['type']=='field':
                    value = self.get_value(browser, attrs['name'])
#TODO: test this
                    if value == '' and 'default' in attrs:
                        value = attrs['default']
                    el = etree.SubElement(parent, node.tag)
                    el.text = tounicode(value)
#TODO: test this
                    for key, value in attrs.iteritems():
                        if key not in ('type', 'name', 'default'):
                            el.set(key, value)

                elif attrs['type']=='attachment':
                    model = browser._name
                    value = self.get_value(browser, attrs['name'])

                    ids = self.pool['ir.attachment'].search(self.cr, self.uid, [('res_model','=',model),('res_id','=',int(value))])
                    datas = self.pool['ir.attachment'].read(self.cr, self.uid, ids)

                    if len(datas):
                        # if there are several, pick first
                        datas = datas[0]
                        fname = str(datas['datas_fname'])
                        ext = fname.split('.')[-1].lower()
                        if ext in ('jpg','jpeg', 'png'):
                            import base64
                            from StringIO import StringIO
                            dt = base64.decodestring(datas['datas'])
                            fp = StringIO()
                            fp.write(dt)
                            i = str(len(self.bin_datas))
                            self.bin_datas[i] = fp
                            el = etree.SubElement(parent, node.tag)
                            el.text = i

                elif attrs['type']=='data':
#TODO: test this
                    txt = self.datas.get('form', {}).get(attrs['name'], '')
                    el = etree.SubElement(parent, node.tag)
                    el.text = txt

                elif attrs['type']=='function':
                    if attrs['name'] in self.func:
                        txt = self.func[attrs['name']](node)
                    else:
                        txt = print_fnc.print_fnc(attrs['name'], node)
                    el = etree.SubElement(parent, node.tag)
                    el.text = txt

                elif attrs['type']=='eval':
                    value = self.eval(browser, attrs['expr'])
                    el = etree.SubElement(parent, node.tag)
                    el.text = str(value)

                elif attrs['type']=='fields':
                    fields = attrs['name'].split(',')
                    vals = {}
                    for b in browser:
                        value = tuple([self.get_value2(b, f) for f in fields])
                        if not value in vals:
                            vals[value]=[]
                        vals[value].append(b)
                    keys = vals.keys()
                    keys.sort()

                    if 'order' in attrs and attrs['order']=='desc':
                        keys.reverse()

                    v_list = [vals[k] for k in keys]
                    for v in v_list:
                        el = etree.SubElement(parent, node.tag)
                        for el_cld in node:
                            self.parse_node(el_cld, el, v)

                elif attrs['type']=='call':
                    if len(attrs['args']):
#TODO: test this
                        # fetches the values of the variables which names where passed in the args attribute
                        args = [self.eval(browser, arg) for arg in attrs['args'].split(',')]
                    else:
                        args = []
                    # get the object
                    if 'model' in attrs:
                        obj = self.pool[attrs['model']]
                    else:
                        obj = browser       # the record(set) is an instance of the model

                    # get the ids
                    if 'ids' in attrs:
                        ids = self.eval(browser, attrs['ids'])
                    else:
                        ids = browse.ids

                    # call the method itself
                    newdatas = getattr(obj, attrs['name'])(self.cr, self.uid, ids, *args)

                    def parse_result_tree(node, parent, datas):
                        if not node.tag == etree.Comment:
                            el = etree.SubElement(parent, node.tag)
                            atr = self.node_attrs_get(node)
                            if 'value' in atr:
                                if not isinstance(datas[atr['value']], (str, unicode)):
                                    txt = str(datas[atr['value']])
                                else:
                                    txt = datas[atr['value']]
                                el.text = txt
                            else:
                                for el_cld in node:
                                    parse_result_tree(el_cld, el, datas)
                    if not isinstance(newdatas, (BaseModel, list)):
                        newdatas = [newdatas]
                    for newdata in newdatas:
                        parse_result_tree(node, parent, newdata)

                elif attrs['type']=='zoom':
                    value = self.get_value(browser, attrs['name'])
                    if value:
                        if not isinstance(value, (BaseModel, list)):
                            v_list = [value]
                        else:
                            v_list = value
                        for v in v_list:
                            el = etree.SubElement(parent, node.tag)
                            for el_cld in node:
                                self.parse_node(el_cld, el, v)
            else:
                # if there is no "type" attribute in the node, copy it to the xml data and parse its children
                if not node.tag == etree.Comment:
                    if node.tag == parent.tag:
                        el = parent
                    else:
                        el = etree.SubElement(parent, node.tag)
                    for el_cld in node:
                        self.parse_node(el_cld,el, browser)
    def xml_get(self):
        return etree.tostring(self.doc,encoding="utf-8",xml_declaration=True,pretty_print=True)

    def parse_tree(self, ids, model, context=None):
        if not context:
            context={}
        browser = self.pool[model].browse(self.cr, self.uid, ids, context)
        self.parse_node(self.dom, self.doc, browser)

    def parse_string(self, xml, ids, model, context=None):
        if not context:
            context={}
        # parses the xml template to memory
        self.dom = etree.XML(xml)
        # create the xml data from the xml template
        self.parse_tree(ids, model, context)

    def parse(self, filename, ids, model, context=None):
        if not context:
            context={}
        # parses the xml template to memory
        src_file = tools.file_open(filename)
        try:
            self.dom = etree.XML(src_file.read())
            self.doc = etree.Element(self.dom.tag)
            self.parse_tree(ids, model, context)
        finally:
            src_file.close()

    def close(self):
        self.doc = None
        self.dom = None


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

