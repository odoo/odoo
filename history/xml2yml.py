# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 OpenERP SA (<http://openerp.com>).
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

"""
Experimental script for conversion between OpenERP's XML serialization format
and the new YAML serialization format introduced in OpenERP 6.0.
Intended to be used as a quick preprocessor for converting data/test files, then
to be fine-tuned manually.
"""

import yaml
import logging
from lxml import etree

__VERSION__ = '0.0.2'

def toString(value):
    value='"' + value + '"'
    return value

class XmlTag(etree.ElementBase):
    def _to_yaml(self):
        child_tags = []
        for node in self:
            if hasattr(node, '_to_yaml'):
                child_tags.append(node._to_yaml())
        return self.tag(attrib=self.attrib, child_tags=child_tags)

class YamlTag(object):
    """
    Superclass for constructors of custom tags defined in yaml file.
    """
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.attrib = self.__dict__.get('attrib', {})
        self.child_tags = self.__dict__.get('child_tags', '')
    def __getitem__(self, key):
        return getattr(self, key)
    def __getattr__(self, attr):
        return None
    def __repr__(self):
        for k,v in self.attrib.iteritems():
            if str(v) and str(v)[0] in ['[', '{', '#', '*', '(']:
                self.attrib[k] = toString(self.attrib[k]).replace("'", '')
        st = self.yaml_tag + ' ' + str(self.attrib)
        return st

# attrib tags
class ref(YamlTag):
    yaml_tag = u'!ref'
    def __init__(self, expr="False"):
        self.expr = expr
    def __repr__(self):
        return "'%s'"%str(self.expr)

class Eval(YamlTag):
    yaml_tag = u'!eval'
    def __init__(self, expr="False"):
        self.expr = expr
    def __repr__(self):
        value=str(self.expr)
        if value.find("6,") != -1:
            value = eval(str(eval(value)))
            value=value[0][2]
            value = [[value]]
        else:
            try:
                value=int(value)
            except:
                if value and value[0] in ['[', '{', '#', '*', '(']:
                    value = value.replace('"', r'\"')
                    value = toString(value)
                else:
                    try:
                        value = eval(value)
                    except Exception:
                        pass
        return value

class Search(YamlTag):
    yaml_tag = u'!ref'

# test tag
class xml_test(XmlTag):
    def _to_yaml(self):
        expr = self.attrib.get('expr')
        text = self.text
        if text:
            expr = expr + ' == ' + '"%s"'%text
        return [[expr]]

class xml_data(etree.ElementBase):
    def _to_yaml(self):
        value = self.attrib.get('noupdate', "0")
        return data(value)

# field tag:
class xml_field(etree.ElementBase):
    def _to_yaml(self):
        field = '  ' + self.attrib.pop('name','unknown')

        if self.attrib.get('search', None):
            value = Search(attrib=self.attrib, child_tags='').__repr__()
        else:
            attr = (self.attrib.get('ref', None) and 'ref') or (self.attrib.get('eval', None) and 'eval') or 'None'
            value = Eval(self.attrib.get(attr, self.text)).__repr__() or ''
        return {field: value}

# value tag
class xml_value(etree.ElementBase):
    def _to_yaml(self):

        if self.attrib.get('eval', None):
            key, val = 'eval', '"'+self.attrib.get('eval')+'"'
        elif self.attrib.get('model', None):
            key, val = 'model', self.attrib.get('model')
        val=val.replace("'",'""')
        self.attrib.pop(key)
        d={}
        for k,v in self.attrib.iteritems():
            if k == 'search':
                v = '"' + v + '"'
            k='--' + k
            v=v.replace("'",'""')
            d[k] = v
        if d:
            ls=[[{key:val},dict(d)]]
        else:
            ls=[[{key:val}]]
        return ls

# data tag
class data(YamlTag):
    yaml_tag = u'!context'
    def __init__(self, noupdate="0"):
        self.child_tags = {'    noupdate':noupdate}
    def __repr__(self):
        return "!!context"

# Record tag
class Record(YamlTag):
    yaml_tag = u'!record'
class xml_record(XmlTag):
    tag=Record
    def _to_yaml(self):
        child_tags = {}
        for node in self:
            if hasattr(node, '_to_yaml'):
                child_tags.update(node._to_yaml())
        return Record(attrib=self.attrib, child_tags=child_tags)

# ir_set tag
class Ir_Set(YamlTag):
    yaml_tag = u'!ir_set'
    def __repr__(self):
        st = self.yaml_tag
        return st
class xml_ir_set(XmlTag):
    tag=Ir_Set
    def _to_yaml(self):
        child_tags = {}
        for node in self:
            if hasattr(node, '_to_yaml'):
                child_tags.update(node._to_yaml())
        return Ir_Set(attrib=self.attrib, child_tags=child_tags)

# workflow tag
class Workflow(YamlTag):
    yaml_tag = u'!workflow'
class xml_workflow(XmlTag):
    tag=Workflow

# function tag
class Function(YamlTag):
    yaml_tag = u'!function'
class xml_function(XmlTag):
    tag=Function

# function tag
class Assert(YamlTag):
    yaml_tag = u'!assert'
class xml_assert(XmlTag):
    tag=Assert

# menuitem tagresult.append(yaml.safe_dump(obj, default_flow_style=False, allow_unicode=True).replace("'",''))
class MenuItem(YamlTag):
    yaml_tag = u'!menuitem'
class xml_menuitem(XmlTag):
    tag=MenuItem

# act_window tag
class ActWindow(YamlTag):
    yaml_tag = u'!act_window'
class xml_act_window(XmlTag):
    tag=ActWindow

# report tag
class Report(YamlTag):
    yaml_tag = u'!report'
class xml_report(XmlTag):
    tag=Report

# deletes tag
class Delete(YamlTag):
    yaml_tag = u'!delete'
class xml_delete(XmlTag):
    tag=Delete

# python tag
class Python(YamlTag):
    yaml_tag = u'!python'
class xml_python(XmlTag):
    tag=Python

# context tag
class Context(YamlTag):
    yaml_tag = u'!context'
class xml_context(XmlTag):
    tag=Context

# url tag
class Url(YamlTag):
    yaml_tag = u'!url'
class xml_url(XmlTag):
    tag=Url

# delete tag
class Delete(YamlTag):
    yaml_tag = u'!delete'
class xml_delete(XmlTag):
    tag=Delete

def represent_data(dumper, data):
        return dumper.represent_mapping(u'tag:yaml.org,2002:map', [('!'+str(data), data.child_tags)])

yaml.SafeDumper.add_representer(Record, represent_data)
yaml.SafeDumper.add_representer(data, represent_data)
yaml.SafeDumper.add_representer(Workflow, represent_data)
yaml.SafeDumper.add_representer(Function, represent_data)
yaml.SafeDumper.add_representer(Assert, represent_data)
yaml.SafeDumper.add_representer(MenuItem, represent_data)
yaml.SafeDumper.add_representer(Ir_Set, represent_data)
yaml.SafeDumper.add_representer(Python, represent_data)
yaml.SafeDumper.add_representer(Context, represent_data)

class MyLookup(etree.CustomElementClassLookup):
    def lookup(self, node_type, document, namespace, name):
        if node_type=='element':
            return {
                'data': xml_data,
                'record': xml_record,
                'field': xml_field,
                'workflow': xml_workflow,
                'function': xml_function,
                'value': xml_value,
                'assert': xml_assert,
                'test': xml_test,
                'menuitem': xml_menuitem,
                'act_window': xml_act_window,
                'report': xml_report,
                'delete': xml_delete,
                'python': xml_python,
                'context': xml_context,
                'url': xml_url,
                'ir_set': xml_ir_set,
            }.get(name, None)
        elif node_type=='comment':
            return None#xml_comment
        return None

class xml_parse(object):
    def __init__(self):
        self.context = {}
    def parse(self, fname):
        parser = etree.XMLParser()
        parser.setElementClassLookup(MyLookup())
        result = []
        self.root = etree.XML(file(fname).read(), parser)
        for data in self.root:
            if hasattr(data, '_to_yaml'):
                obj = data._to_yaml()
                if obj.yaml_tag == '!context':
                    result.append(yaml.dump(str(obj)).replace("'",'').split('\n')[0])
                    result.append(yaml.dump(obj.child_tags, default_flow_style=False).replace("'",''))
                else:
                    result.append(yaml.safe_dump(obj, default_flow_style=False, allow_unicode=True).replace("'",''))
            self.context.update(data.attrib)
            for tag in data:
                if tag.tag == etree.Comment:
                    result.append(tag)
                else:
                    if hasattr(tag, '_to_yaml'):
                        obj = tag._to_yaml()
                        if not obj.child_tags:
                            result.append(yaml.dump('!'+str(obj), default_flow_style=False, allow_unicode=True, width=999).replace("'",''))
                        else:
                            result.append(yaml.safe_dump(obj, default_flow_style=False, allow_unicode=True, width=999).replace('\n:', ':\n').replace("'",''))
        print "# Experimental OpenERP xml-to-yml conversion! (v%s)"%__VERSION__
        print "# Please use this as a first conversion/preprocessing step,"
        print "# not as a production-ready tool!"
        for record in result:
            if type(record) != type(''):
                record=str(record)
                l= record.split("\n")
                for line in l:
                    print '#' + str(line)
                continue
            record=str(record)
            record = record.replace('- --','  ')        #for value tag
            record = record.replace('!!', '- \n  !')    #for all parent tags
            record = record.replace('- - -', '    -')   #for many2many fields
            record = record.replace('? ', '')           #for long expressions
            record = record.replace('""', "'")          #for string-value under value tag
            print record

if __name__=='__main__':
    import optparse
    import sys
    parser = optparse.OptionParser(
        usage = '%s file.xml' % sys.argv[0])
    (opt, args) = parser.parse_args()
    if len(args) != 1:
        parser.error("incorrect number of arguments")
    fname = sys.argv[1]
    p = xml_parse()
    p.parse(fname)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
