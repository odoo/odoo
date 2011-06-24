# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


class mapper(object):
    """
        super class for all mapper class
        They are call before import data
        to transform the mapping into real value that we
        will import
        
        the call function receive a dictionary with external data
            'external_field' : value
    """
    def __call__(self, external_values):
        raise NotImplementedError()

class dbmapper(mapper):
    """
        Super class for mapper that need to access to 
        data base or any function of the import_framework
        
        self.parent contains a reference to the instance of
        the import framework
    """
    def set_parent(self, parent):
        self.parent = parent
        

class concat(mapper):
    """
        Use : contact('field_name1', 'field_name2', delimiter='_')
        concat value of fields using the delimiter, delimiter is optional
        and by default is a space
        
    """
    def __init__(self, *arg, **delimiter):
        self.arg = arg
        self.delimiter = delimiter and delimiter.get('delimiter', ' ') or ' '
        
    def __call__(self, external_values):
        return self.delimiter.join(map(lambda x : external_values.get(x,''), self.arg))
    
class ppconcat(mapper):
    """
        Use : contact('field_name1', 'field_name2', delimiter='_')
        concat external field name and value of fields using the delimiter, 
        delimiter is optional and by default is a two line feeds
        
    """
    def __init__(self, *arg, **delimiter):
        self.arg = arg
        self.delimiter = delimiter and delimiter.get('delimiter', ' ') or '\n\n'
        
    def __call__(self, external_values):
        return self.delimiter.join(map(lambda x : x + ": " + external_values.get(x,''), self.arg))
    
class const(mapper):
    """
        Use : const(arg)
        return always arg
    """
    def __init__(self, val):
        self.val = val
        
    def __call__(self, external_values):
        return self.val 
    
class value(mapper):
    """
        Use : value(external_field_name)
        Return the value of the external field name
        this is equivalent to the a single string
        
        usefull for call if you want your call get the value
        and don't care about the name of the field
        call(self.method, value('field1'))
    """
    def __init__(self, val, default='', fallback=False):
        self.val = val
        self.default = default
        self.fallback = fallback
        
    def __call__(self, external_values):
        val = external_values.get(self.val, self.default) 
        if self.fallback and (not val or val == self.default):
            val = external_values.get(self.fallback, self.default)
        return val 
    

    
class map_val(mapper):
    """
        Use : map_val(external_field, val_mapping)
        where val_mapping is a dictionary 
        with external_val : openerp_val
        
        usefull for selection field like state
        to map value 
    """
    def __init__(self, val, map, default='draft'):
        self.val = value(val)
        self.map = map
        self.default = default
        
    def __call__(self, external_values):
        return self.map.get(self.val(external_values), self.default)
    
class ref(dbmapper):
    """
        Use : ref(table_name, external_id)
        return the xml_id of the ressource
        
        to associate an already imported object with the current object
    """
    def __init__(self, table, field_name):
        self.table = table
        self.field_name = field_name
        
    def __call__(self, external_values):
        return self.parent.xml_id_exist(self.table, external_values.get(self.field_name))
  
class refbyname(dbmapper):  
    """
        Use : refbyname(table_name, external_name, res.model)
        same as ref but use the name of the ressource to find it
    """
    def __init__(self, table, field_name, model):
        self.table = table
        self.field_name = field_name
        self.model = model
        
    def __call__(self, external_values):
        v = external_values.get(self.field_name, '')
        return self.parent.name_exist(self.table, v , self.model)
        
class call(mapper):
    """
        Use : call(function, arg1, arg2)
        to call the function with external val follow by the arg specified 
    """
    def __init__(self, fun, *arg):
        self.fun = fun
        self.arg = arg
    
    def __call__(self, external_values):
        args = []
        for arg in self.arg:
            if isinstance(arg, mapper):
                args.append(arg(external_values))
            else:
                args.append(arg)
        return self.fun(external_values, *args)
    
    