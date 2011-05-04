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
import tools
import pytz
import time
from datetime import datetime, timedelta, date
from dateutil import parser
import dateutil


MODULE_NAME = 'sugarcrm_import'


DO_NOT_FIND_DOMAIN = [('id', '=', 0)]


def find_mapped_id(obj, cr, uid, res_model, xml_id, context=None):
    return obj.pool.get('ir.model.data')._get_id(cr, uid, MODULE_NAME, xml_id)

def xml_id_exist(obj, cr, uid, table, sugar_id, context=None):
    xml_id = generate_xml_id(sugar_id, table)
    id = obj.pool.get('ir.model.data')._get_id(cr, uid, MODULE_NAME, xml_id)
    return id and xml_id or False


def mapped_id(obj, cr, uid, res_model, sugar_id, id, context=None):
    """
        This function create the mapping between an already existing data and the similar data of sugarcrm
        @param res_model: model of the mapped object
        @param sugar_id: external sugar id
        @param id: id in the database
        
        @return : the xml_id or sugar_id 
    """
    if not context:
        context = {}
    ir_model_data_obj = obj.pool.get('ir.model.data')
    id = ir_model_data_obj._update(cr, uid, res_model,
                     MODULE_NAME, {}, mode='update', xml_id=sugar_id,
                     noupdate=True, res_id=id, context=context)
    return sugar_id




def mapped_id_if_exist(sugar_obj, cr, uid, model, domain, xml_id, context=None):
    """
        @param domain : search domain to find existing record, should return a unique record
        @param xml_id: xml_id give to the mapping
        
        @return : the xml_id if the record exist in the db, False otherwise
    """
    obj = sugar_obj.pool.get(model)
    ids = obj.search(cr, uid, domain, context=context)
    #print "ids", ids, "domain", domain
    if ids:
        return mapped_id(obj, cr, uid, model, xml_id, ids[0], context=context)
    return False

def import_module(obj, cr, uid, model, mapping, datas, table, context=None):
    """
        @param mapping : definition of the mapping
                         @see: sugarcrm_fields_mapp
        @param datas : list of dictionnaries 
            datas = [data_1, data_2, ..]
            data_i is a map external field_name => value
            and each data_i have a external id => in data_id['id']
    """
    mapping['id'] = 'id_new'
    res = []
    for data in datas:
        self_dependencies = []
        for k in data.keys():
            if '_new' in k:
                self_dependencies.append(k[:-4])
        
        data['id_new'] = generate_xml_id(data['id'], table)
        fields, values = sugarcrm_fields_mapp(data, mapping, context)
        res.append(values)
    
    model_obj = obj.pool.get(model)
    model_obj.import_data(cr, uid, fields, res, mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    for field in self_dependencies:
        import_self_dependencies(model_obj, cr, uid, field, datas, context)
    
def import_object_mapping(sugar_obj, cr, uid, mapping, data, model, table, name, domain_search=False, context=None):
    fields, datas = sugarcrm_fields_mapp(data, mapping, context)
    return import_object(sugar_obj, cr, uid, fields, datas, model, table, name, domain_search, context=context)

def import_object(sugar_obj, cr, uid, fields, data, model, table, name, domain_search=False,  context=None):
    """
        This method will import an object in the openerp, usefull for field that is only a char in sugar and is an object in openerp
        use import_data that will take care to create/update or do nothing with the data
        this method return the xml_id
        @param fields: list of fields needed to create the object without id
        @param data: the list of the data, in the same order as the field
            ex : fields = ['firstname', 'lastname'] ; data = ['John', 'Mc donalds']
        @param model: the openerp's model of the create/update object
        @param table: the table where data come from in sugarcrm, no need to fit the real name of openerp name, just need to be unique
        @param unique_name: the name of the object that we want to create/update get the id
        @param domain_search : the domain that should find the unique existing record
        
        @return: the xml_id of the ressources
    """
    if not context:
        context = {}
    domain_search = not domain_search and [('name', 'ilike', name)] or domain_search
    obj = sugar_obj.pool.get(model)
    xml_id = generate_xml_id(name, table)
    
    xml_ref = mapped_id_if_exist(obj, cr, uid, model, domain_search, xml_id, context=context)
    fields.append('id')
    data.append(xml_id)
    obj.import_data(cr, uid, fields, [data], mode='update', current_module=MODULE_NAME, noupdate=True, context=context)
    return xml_ref or xml_id


def add_m2o_data(data, fields, column, xml_ids):
    """
        @param fields: list of fields
        @param data: the list of the data, in the same order as the field
            ex : fields = ['firstname', 'lastname'] ; data = ['John', 'Mc donalds']
        @param column : name of the column that will contains the xml_id of o2m data
            ex : contact_id/id
        @param xml_ids : the list of xml id of the data
        
        @return fields and data with the last column "column", "xml_id1,xml_id2,xml_id3,.."
    """
    fields.append(column)
    data.append(','.join(xml_ids))    
    return fields, data

#TODO for more then one field that need parent
def import_self_dependencies(obj, cr, uid, parent_field, datas, context):
    """
        @param parent_field: the name of the field that generate a self_dependencies, we call the object referenced in this
            field the parent of the object
        @param datas: a list of dictionnaries
            Dictionnaries need to contains 
                id_new : the xml_id of the object
                field_new : the xml_id of the parent
    """
    fields = ['id', parent_field+'/id']
    for data in datas:
        if data.get(parent_field + '_new'):
            values = [data['id_new'], data[parent_field + '_new']]
            obj.import_data(cr, uid, fields, [values], mode='update', current_module=MODULE_NAME, noupdate=True, context=context) 
    

def generate_xml_id(name, table):
    """
        @param name: name of the object, has to be unique in for a given table
        @param table : table where the record we want generate come from
        @return: a unique xml id for record, the xml_id will be the same given the same table and same name
                 To be used to avoid duplication of data that don't have ids
    """
    sugar_instance = "sugarcrm" #TODO need to be changed we information is known in the wizard
    name = name.replace('.', '_')
    return sugar_instance + "_" + table + "_" + name




def sugarcrm_fields_mapp(dict_sugar, openerp_dict, context=None):
    #TODO write documentation
    if not context:
        context = {}
    if 'tz' in context and context['tz']:
        time_zone = context['tz']
    else:
        time_zone = tools.get_server_timezone()
    au_tz = pytz.timezone(time_zone)
    fields=[]
    data_lst = []
    for key,val in openerp_dict.items():
        if key not in fields and dict_sugar:
            fields.append(key)
            if isinstance(val, list) and val:
                #Allow to print a bit more pretty way long list of data in the same field
                if len(val) >= 1 and val[0] == "__prettyprint__":
                    val = val[1:]
                    data_lst.append('\n\n'.join(map(lambda x : x + ": " + dict_sugar.get(x,''), val)))
                elif val[0] == '__datetime__':
                    val = val[1]
                    if dict_sugar.get(val) and len(dict_sugar.get(val))<=10:
                        updated_dt = date.fromtimestamp(time.mktime(time.strptime(dict_sugar.get(val), '%Y-%m-%d'))) or False
                    elif  dict_sugar.get(val):
                        convert_date = datetime.strptime(dict_sugar.get(val), '%Y-%m-%d %H:%M:%S')
                        edate = convert_date.replace(tzinfo=au_tz)
                        au_dt = au_tz.normalize(edate.astimezone(au_tz))
                        updated_dt = datetime(*au_dt.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        updated_dt = False    
                    data_lst.append(updated_dt)
                else:
                    if key == 'duration':
                        data_lst.append('.'.join(map(lambda x : dict_sugar.get(x,''), val)))
                    else:
                        data_lst.append(' '.join(map(lambda x : dict_sugar.get(x,''), val)))
            else:
                data_lst.append(dict_sugar.get(val,''))
    return fields,data_lst