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
import pprint
import mapper
import pooler
import tools
from tools.translate import _

from threading import Thread
import datetime
import logging
import StringIO
import traceback
pp = pprint.PrettyPrinter(indent=4)
_logger = logging.getLogger(__name__)



class import_framework(Thread):
    """
        This class should be extends,
        get_data and get_mapping have to extends
        get_state_map and initialize can be extended
        for advanced purpose get_default_hook can also be extended
        @see dummy import for a minimal exemple
    """

    """
        for import_object, this domain will avoid to find an already existing object
    """
    DO_NOT_FIND_DOMAIN = [('id', '=', 0)]

    #TODO don't use context to pass credential parameters
    def __init__(self, obj, cr, uid, instance_name, module_name, email_to_notify=False, context=None):
        Thread.__init__(self)
        self.external_id_field = 'id'
        self.obj = obj
        self.cr = cr
        self.uid = uid
        self.instance_name = instance_name
        self.module_name = module_name
        self.context = context or {}
        self.email = email_to_notify
        self.table_list = []
        self.initialize()

    """
        Abstract Method to be implemented in
        the real instance
    """
    def initialize(self):
        """
            init before import
            usually for the login
        """
        pass

    def init_run(self):
        """
            call after intialize run in the thread, not in the main process
            TO use for long initialization operation
        """
        pass

    def get_data(self, table):
        """
            @return: a list of dictionaries
                each dictionnaries contains the list of pair  external_field_name : value
        """
        return [{}]

    def get_link(self, from_table, ids, to_table):
        """
            @return: a dictionaries that contains the association between the id (from_table)
                     and the list (to table) of id linked
        """
        return {}

    def get_external_id(self, data):
        """
            @return the external id
                the default implementation return self.external_id_field (that has 'id') by default
                if the name of id field is different, you can overwrite this method or change the value
                of self.external_id_field
        """
        return data[self.external_id_field]

    def get_mapping(self):
        """
            @return: { TABLE_NAME : {
                'model' : 'openerp.model.name',
                #if true import the table if not just resolve dependencies, use for meta package, by default => True
                #Not required
                'import' : True or False,
                #Not required
                'dependencies' : [TABLE_1, TABLE_2],
                #Not required
                'hook' : self.function_name, #get the val dict of the object, return the same val dict or False
                'map' : { @see mapper
                    'openerp_field_name' : 'external_field_name', or val('external_field_name')
                    'openerp_field_id/id' : ref(TABLE_1, 'external_id_field'), #make the mapping between the external id and the xml on the right
                    'openerp_field2_id/id_parent' : ref(TABLE_1,'external_id_field') #indicate a self dependencies on openerp_field2_id
                    'state' : map_val('state_equivalent_field', mapping), # use get_state_map to make the mapping between the value of the field and the value of the state
                    'text_field' : concat('field_1', 'field_2', .., delimiter=':'), #concat the value of the list of field in one
                    'description_field' : ppconcat('field_1', 'field_2', .., delimiter='\n\t'), #same as above but with a prettier formatting
                    'field' : call(callable, arg1, arg2, ..), #call the function with all the value, the function should send the value : self.callable
                    'field' : callable
                    'field' : call(method, val('external_field') interface of method is self, val where val is the value of the field
                    'field' : const(value) #always set this field to value
                    + any custom mapper that you will define
                }
            },

            }
        """
        return {}

    def default_hook(self, val):
        """
            this hook will be apply on each table that don't have hook
            here we define the identity hook
        """
        return val

    def _import_table(self, table):
        data = self.get_data(table)
        map = self.get_mapping()[table]['map']
        hook = self.get_mapping()[table].get('hook', self.default_hook)
        model = self.get_mapping()[table]['model']

        final_data = []
        for val in data:
            res = hook(val)
            if res:
                final_data.append(res)
        return self._save_data(model, dict(map), final_data, table)

    def _save_data(self, model, mapping, datas, table):
        """
            @param model: the model of the object to import
            @param table : the external table where the data come from
            @param mapping : definition of the mapping
                             @see: get_mapping
            @param datas : list of dictionnaries
                datas = [data_1, data_2, ..]
                data_i is a map external field_name => value
                and each data_i have a external id => in data_id['id']
        """
        _logger.info(' Importing %s into %s' % (table, model))
        if not datas:
            return (0, 'No data found')
        mapping['id'] = 'id_new'
        res = []


        self_dependencies = []
        for k in mapping.keys():
            if '_parent' in k:
                self_dependencies.append((k[:-7], mapping.pop(k)))

        for data in datas:
            for k, field_name in self_dependencies:
                data[k] = data.get(field_name) and self._generate_xml_id(data.get(field_name), table)

            data['id_new'] = self._generate_xml_id(self.get_external_id(data), table)
            fields, values = self._fields_mapp(data, mapping, table)
            res.append(values)

        model_obj = self.obj.pool.get(model)
        if not model_obj:
            raise ValueError(_("%s is not a valid model name") % model)
        _logger.debug(_(" fields imported : ") + str(fields))
        (p, r, warning, s) = model_obj.import_data(self.cr, self.uid, fields, res, mode='update', current_module=self.module_name, noupdate=True, context=self.context)
        for (field, field_name) in self_dependencies:
            self._import_self_dependencies(model_obj, field, datas)
        return (len(res), warning)

    def _import_self_dependencies(self, obj, parent_field, datas):
        """
            @param parent_field: the name of the field that generate a self_dependencies, we call the object referenced in this
                field the parent of the object
            @param datas: a list of dictionnaries
                Dictionnaries need to contains
                    id_new : the xml_id of the object
                    field_new : the xml_id of the parent
        """
        fields = ['id', parent_field]
        for data in datas:
            if data.get(parent_field):
                values = [data['id_new'], data[parent_field]]
                obj.import_data(self.cr, self.uid, fields, [values], mode='update', current_module=self.module_name, noupdate=True, context=self.context)

    def _preprocess_mapping(self, mapping):
        """
            Preprocess the mapping :
            after the preprocces, everything is
            callable in the val of the dictionary

            use to allow syntaxical sugar like 'field': 'external_field'
            instead of 'field' : value('external_field')
        """
        map = dict(mapping)
        for key, value in map.items():
            if isinstance(value, basestring):
                map[key] = mapper.value(value)
            #set parent for instance of dbmapper
            elif isinstance(value, mapper.dbmapper):
                value.set_parent(self)
        return map


    def _fields_mapp(self,dict_sugar, openerp_dict, table):
        """
            call all the mapper and transform data
            to be compatible with import_data
        """
        fields=[]
        data_lst = []
        mapping = self._preprocess_mapping(openerp_dict)
        for key,val in mapping.items():
            if key not in fields and dict_sugar:
                fields.append(key)
                value = val(dict(dict_sugar))
                data_lst.append(value)
        return fields, data_lst

    def _generate_xml_id(self, name, table):
        """
            @param name: name of the object, has to be unique in for a given table
            @param table : table where the record we want generate come from
            @return: a unique xml id for record, the xml_id will be the same given the same table and same name
                     To be used to avoid duplication of data that don't have ids
        """
        sugar_instance = self.instance_name
        name = name.replace('.', '_').replace(',', '_')
        return sugar_instance + "_" + table + "_" + name


    """
        Public interface of the framework
        those function can be use in the callable function defined in the mapping
    """
    def xml_id_exist(self, table, external_id):
        """
            Check if the external id exist in the openerp database
            in order to check if the id exist the table where it come from
            should be provide
            @return the xml_id generated if the external_id exist in the database or false
        """
        if not external_id:
            return False

        xml_id = self._generate_xml_id(external_id, table)
        id = self.obj.pool.get('ir.model.data').search(self.cr, self.uid, [('name', '=', xml_id), ('module', '=', self.module_name)])
        return id and xml_id or False

    def name_exist(self, table, name, model):
        """
            Check if the object with the name exist in the openerp database
            in order to check if the id exist the table where it come from
            should be provide and the model of the object
        """
        fields = ['name']
        data = [name]
        return self.import_object(fields, data, model, table, name, [('name', '=', name)])

    def get_mapped_id(self, table, external_id, context=None):
        """
            @return return the databse id linked with the external_id
        """
        if not external_id:
            return False

        xml_id = self._generate_xml_id(external_id, table)
        return self.obj.pool.get('ir.model.data').get_object_reference(self.cr, self.uid, self.module_name, xml_id)[1]

    def import_object_mapping(self, mapping, data, model, table, name, domain_search=False):
        """
            same as import_objects but instead of two list fields and data,
            this method take a dictionnaries : external_field : value
                            and the mapping similar to the one define in 'map' key
            @see import_object, get_mapping
        """
        fields, datas = self._fields_mapp(data, mapping, table)
        return self.import_object(fields, datas, model, table, name, domain_search)

    def import_object(self, fields, data, model, table, name, domain_search=False):
        """
            This method will import an object in the openerp, usefull for field that is only a char in sugar and is an object in openerp
            use import_data that will take care to create/update or do nothing with the data
            this method return the xml_id

            To be use, when you want to create an object or link if already exist
            use DO_NOT_LINK_DOMAIN to create always a new object
            @param fields: list of fields needed to create the object without id
            @param data: the list of the data, in the same order as the field
                ex : fields = ['firstname', 'lastname'] ; data = ['John', 'Mc donalds']
            @param model: the openerp's model of the create/update object
            @param table: the table where data come from in sugarcrm, no need to fit the real name of openerp name, just need to be unique
            @param unique_name: the name of the object that we want to create/update get the id
            @param domain_search : the domain that should find the unique existing record

            @return: the xml_id of the ressources
        """
        domain_search = not domain_search and [('name', 'ilike', name)] or domain_search
        obj = self.obj.pool.get(model)
        if not obj: #if the model doesn't exist
            return False

        xml_id = self._generate_xml_id(name, table)
        xml_ref = self.mapped_id_if_exist(model, domain_search, table, name)
        fields.append('id')
        data.append(xml_id)
        obj.import_data(self.cr, self.uid, fields, [data], mode='update', current_module=self.module_name, noupdate=True, context=self.context)
        return xml_ref or xml_id


    def mapped_id_if_exist(self, model, domain, table, name):
        """
            To be use when we want link with and existing object, if the object don't exist
            just ignore.
            @param domain : search domain to find existing record, should return a unique record
            @param xml_id: xml_id give to the mapping
            @param name: external_id or name of the object to create if there is no id
            @param table: the name of the table of the object to map
            @return : the xml_id if the record exist in the db, False otherwise
        """
        obj = self.obj.pool.get(model)
        ids = obj.search(self.cr, self.uid, domain, context=self.context)
        if ids:
            xml_id = self._generate_xml_id(name, table)
            ir_model_data_obj = obj.pool.get('ir.model.data')
            id = ir_model_data_obj._update(self.cr, self.uid, model,
                             self.module_name, {}, mode='update', xml_id=xml_id,
                             noupdate=True, res_id=ids[0], context=self.context)
            return xml_id
        return False


    def set_table_list(self, table_list):
        """
            Set the list of table to import, this method should be call before run
            @param table_list: the list of external table to import
               ['Leads', 'Opportunity']
        """
        self.table_list = table_list

    def run(self):
        """
            Import all data into openerp,
            this is the Entry point to launch the process of import


        """
        self.data_started = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cr = pooler.get_db(self.cr.dbname).cursor()
        error = False
        result = []
        try:
            self.init_run()
            imported = set() #to invoid importing 2 times the sames modules
            for table in self.table_list:
                to_import = self.get_mapping()[table].get('import', True)
                if not table in imported:
                    res = self._resolve_dependencies(self.get_mapping()[table].get('dependencies', []), imported)
                    result.extend(res)
                    if to_import:
                        (position, warning) = self._import_table(table)
                        result.append((table, position, warning))
                    imported.add(table)
            self.cr.commit()

        except Exception, err:
            sh = StringIO.StringIO()
            traceback.print_exc(file=sh)
            error = sh.getvalue()
            print error


        self.date_ended = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._send_notification_email(result, error)

        self.cr.close()

    def _resolve_dependencies(self, dep, imported):
        """
            import dependencies recursively
            and avoid to import twice the same table
        """
        result = []
        for dependency in dep:
            if not dependency in imported:
                to_import = self.get_mapping()[dependency].get('import', True)
                res = self._resolve_dependencies(self.get_mapping()[dependency].get('dependencies', []), imported)
                result.extend(res)
                if to_import:
                    r = self._import_table(dependency)
                    (position, warning) = r
                    result.append((dependency, position, warning))
                imported.add(dependency)
        return result

    def _send_notification_email(self, result, error):
        if not self.email:
            return False	
        email_obj = self.obj.pool.get('mail.message')
        email_id = email_obj.create(self.cr, self.uid, {
            'email_from' : 'import@module.openerp',
            'email_to' : self.email,
            'body_text' : self.get_email_body(result, error),
            'subject' : self.get_email_subject(result, error),
            'auto_delete' : True})
        email_obj.send(self.cr, self.uid, [email_id])
        if error:
            _logger.error(_("Import failed due to an unexpected error"))
        else:
            _logger.info(_("Import finished, notification email sended"))

    def get_email_subject(self, result, error=False):
        """
            This method define the subject of the email send by openerp at the end of import
            @param result: a list of tuple
                (table_name, number_of_record_created/updated, warning) for each table
            @return the subject of the mail

        """
        if error:
            return _("Data Import failed at %s due to an unexpected error") % self.date_ended
        return _("Import of your data finished at %s") % self.date_ended

    def get_email_body(self, result, error=False):
        """
            This method define the body of the email send by openerp at the end of import. The body is separated in two part
            the header (@see get_body_header), and the generate body with the list of table and number of record imported.
            If you want to keep this it's better to overwrite get_body_header
            @param result: a list of tuple
                (table_name, number_of_record_created/updated, warning) for each table
            @return the subject of the mail

        """

        body = _("started at %s and finished at %s \n") % (self.data_started, self.date_ended)
        if error:
            body += _("but failed, in consequence no data were imported to keep database consistency \n error : \n") + error

        for (table, nb, warning) in result:
            if not warning:
                warning = _("with no warning")
            else:
                warning = _("with warning : %s") % warning
            body += _("%s has been successfully imported from %s %s, %s \n") % (nb, self.instance_name, table, warning)
        return self.get_body_header(result) + "\n\n" + body

    def get_body_header(self, result):
        """
            @return the first sentences written in the mail's body
        """
        return _("The import of data \n instance name : %s \n") % self.instance_name


    #TODO documentation test
    def run_test(self):
        back_get_data = self.get_data
        back_get_link = self.get_link
        back_init = self.initialize
        self.get_data = self.get_data_test
        self.get_link = self.get_link_test
        self.initialize = self.intialize_test
        self.run()
        self.get_data = back_get_data
        self.get_link = back_get_link
        self.initialize = back_init

    def get_data_test(self, table):
        return [{}]

    def get_link_test(self, from_table, ids, to_table):
        return {}

    def intialize_test(self):
        pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
