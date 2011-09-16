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

from osv import osv,fields
import hashlib
import json
import time
import base64
import urllib2
import openerp.release as release
from tools.translate import _
import netsvc

def split_xml_id(xml_id):
    assert len(xml_id.split('.'))==2, \
            _("'%s' contains too many dots. XML ids should not contain dots ! These are used to refer to other modules data, as in module.reference_id") % (xml_id)
    return xml_id.split('.')

def safe_unique_id(database_id, model, record_id):
    """Generate a unique string to represent a (database id,model,record_id) pair
    without being too long, without revealing the database id, and
    with a very low probability of collisions.
    """
    msg = "%s-%s-%s-%s" % (time.time(), database_id, model, record_id)
    digest = hashlib.sha1(msg).digest()
    digest = ''.join(chr(ord(x) ^ ord(y)) for (x,y) in zip(digest[:9], digest[9:-2]))
    # finally, use the b64-encoded folded digest as ID part of the unique ID:
    digest = base64.urlsafe_b64encode(digest)
        
    return '%s-%s' % (model.replace('.','_'), digest)

class ir_edi_document(osv.osv):
    _name = 'ir.edi.document'
    _description = 'To represent the EDI Document of any OpenERP record.'
    _columns = {
                'name': fields.char("EDI token", size = 128, help="EDI Token is a unique identifier for the EDI document."),
                'document': fields.text("Document", help="hold the serialization of the EDI document.")
                
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The EDI Token must be unique!')
    ]
    
    
    def new_edi_token(self, cr, uid, record):
        """
        Return a new, random unique token to identify an edi.document
        :param record: It's a object of browse_record of any model
        """
        db_uuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')

        edi_token = hashlib.sha256('%s-%s-%s-%s' % (time.time(), db_uuid, record._name, record.id)).hexdigest()
        return edi_token
    
    def serialize(self, edi_documents):
        """Serialize the list of dictionaries using json dumps method
        perform a JSON serialization of a list of dicts prepared by generate_edi() and return a UTF-8 encoded string that could be passed to deserialize()
        :param edi_dicts: it's list of edi_dict
        """
        serialized_list = json.dumps(edi_documents)
        return serialized_list
    
    def generate_edi(self, cr, uid, records, context=None):
        """
        Generate the list of dictionaries using edi_export method of edi class 
        :param records: it's a object of browse_record_list of any model
        """
        
        edi_list = []
        for record in records:
            record_model_obj = self.pool.get(record._name)
            edi_list += record_model_obj.edi_export(cr, uid, [record], context=context)
        return self.serialize(edi_list)
    
    def get_document(self, cr, uid, edi_token, context=None):
        """
        Get the edi document from database using given edi token 
        returns the string serialization that is in the database (column: document) for the given edi_token or raise.
        """
        
        records = self.name_search(cr, uid, edi_token, operator='=', context=context)
        if records:
            record = records[0][0]
            edi = self.browse(cr, uid, record, context=context)
            return edi.document
        else:  
            pass
    
    def load_edi(self, cr, uid, edi_documents, context=None):
        """
        loads the values from list of dictionaries to the corresponding OpenERP records
        using the edi_import method of edi class
        For each edi record (dict) in the list, call the corresponding osv.edi_import() method, based on the __model attribute (see section 2.4 of  for spec of 
        osv.edi_import)

        :param edi_dicts: list of edi_dict
        """
        module_obj =self.pool.get('ir.module.module')
        res = []
        for edi_document in edi_documents:
            module = edi_document.get('__module')
            module_ids = module_obj.search(cr, uid, [('name','=',module),('state','not in',['uninstalled', 'uninstallable', 'to remove'])])
            if not module_ids:
                raise osv.except_osv(_('Invalid action !'),
                            _('The document you are trying to import requires the OpenERP "%s" application. The OpenERP configuration assistant will help with this if you are connected as an administrator.')%(module))
            model = edi_document.get('__model')
            assert model, _('model should be provided in EDI Dict')
            model_obj = self.pool.get(model)
            record_id = model_obj.edi_import(cr, uid, edi_document, context=context)
            res.append((model,record_id))
        return res
    
    def deserialize(self, edi_document_string):
        """ Deserialized the edi document string
        perform JSON deserialization from an edi document string, and returns a list of dicts
        """
        edi_document = json.loads(edi_document_string)
        
        return edi_document
    
    def export_edi(self, cr, uid, records, context=None):
        """
        The method handles the flow of the edi document generation and store it in 
            the database and return the edi_token of the particular document
        Steps: 
        * call generate_edi() to get a serialization and new_edi_token() to get a unique ID
        * serialize the list returned by generate_edi() using serialize(), and save it in database with unique ID.
        * return the unique ID

        : param records: list of browse_record of any model
        """
        exported_ids = []
        for record in records:
            document = self.generate_edi(cr, uid, [record], context)
            token = self.new_edi_token(cr, uid, record)
            self.create(cr, uid, {
                         'name': token,
                         'document': document
                        }, context=context)
        
            exported_ids.append(token)
        return exported_ids
    
    def import_edi(self, cr, uid, edi_document=None, edi_url=None, context=None):
        """
        The method handles the flow of importing particular edi document and 
        updates the database values on the basis of the edi document using 
        edi_loads method
        
        * N: a serialized edi.document or the URL to download a serialized document
        * If a URL is provided, download it first to get the document
        * Calls deserialize() to get the resulting list of dicts from the document
        * Call load_edi() with the list of dicts, to create or update the corresponding OpenERP records based on the edi.document.
        """
        
        if edi_url and not edi_document:
            edi_document = urllib2.urlopen(edi_url).read()
        assert edi_document, _('EDI Document should be provided')
        edi_documents = self.deserialize(edi_document)
        return self.load_edi(cr, uid, edi_documents, context=context)
    
ir_edi_document()

class edi(object):
    _name = 'edi'
    _description = 'edi document handler'
    
    """Mixin class for OSV objects that want be exposed as EDI documents.
       Classes that inherit from this mixin class should override the 
       ``edi_import()`` and ``edi_export()`` methods to implement their
       specific behavior, based on the primitives provided by this superclass."""

    def record_xml_id(self, cr, uid, record, context=None):
        model_data_pool = self.pool.get('ir.model.data')
        data_ids = model_data_pool.search(cr, uid, [('res_id','=',record.id),('model','=',record._name)])
        if not data_ids:
            return False
        xml_record_id = data_ids[0]
        xml_record = model_data_pool.browse(cr, uid, xml_record_id, context=context)
        return xml_record.module, xml_record.name

    def edi_xml_id(self, cr, uid, record, xml_id=None, context=None):
        """
        Generate a unique string to represent a pair of (the database's UUID, the XML ID).
        Each EDI record and each relationship value are represented using a unique
        database identifier. These database identifiers include the database unique
        ID, as a way to uniquely refer to any record within any OpenERP instance,
        without conflict.

        For OpenERP records that have an existing "XML ID" (i.e. an entry in
        ir.model.data), the EDI unique identifier for this record will be made of
        "%s:%s" % (the database's UUID, the XML ID). The database's UUID MUST
        NOT contain a colon characters (this is guaranteed by the UUID algorithm).

        For OpenERP records that have no existing "XML ID", a new one should be
        created during the EDI export. It is recommended that the generated XML ID
        contains a readable reference to the record model, plus a unique value that
        hides the database ID.
        """
        model_data_pool = self.pool.get('ir.model.data')
        db_uuid = self.pool.get('ir.config_parameter').get_param(cr, uid, 'database.uuid')

        _record_xml = self.record_xml_id(cr, uid, record, context=context)
        if _record_xml:
            module, xml_id = _record_xml
            xml_id = '%s:%s.%s' % (db_uuid, module, xml_id)
        else:
            if not xml_id:
                uuid = safe_unique_id(db_uuid, record._name, record.id)
                xml_id = '%s:%s.%s' % (db_uuid, record._module, uuid)
            module, xml_id2 = split_xml_id(xml_id)
            xml_record_id = model_data_pool.create(cr, uid, {
                'name': xml_id2,
                'model': record._name,
                'module': module,
                'res_id': record.id}, context=context)
        return xml_id
    
    def edi_metadata(self, cr, uid, records, context=None):
        """Return a list representing the boilerplate EDI structure for
           exporting the record in the given browse_rec_list, including
           the metadata fields
        
        The metadata fields MUST always include:
        - __model': the OpenERP model name
        - __module': the OpenERP module containing the model
        - __id': the unique (cross-DB) identifier for this record
        - __last_update': last update date of record, ISO date string in UTC
        - __version': a list of components for the version
        - __attachments': a list (possibly empty) of dicts describing the files attached to this record.
        """
        if context is None:
            context = {}
        data_ids = []
        attachment_object = self.pool.get('ir.attachment')
        edi_dict_list = []
        db_uuid = ''
        version = []
        for ver in release.major_version.split('.'):
            try:
                ver = int(ver)
            except:
                pass
            version.append(ver)

        for record in records:
            attachment_ids = attachment_object.search(cr, uid, [('res_model','=', record._name), ('res_id', '=', record.id)])
            attachment_dict_list = []
            for attachment in attachment_object.browse(cr, uid, attachment_ids, context=context):
                attachment_dict_list.append({
                        'name' : attachment.name,
                        'content': base64.encodestring(attachment.datas),
                        'file_name': attachment.datas_fname,
                })
            
            
            uuid = self.edi_xml_id(cr, uid, record, context=context)
            edi_dict = {
                '__id': uuid,
                '__last_update': False, #record.write_date, #TODO: convert into UTC
            }
            if not context.get('o2m_export'):
                edi_dict.update({
                    '__model' : record._name,
                    '__module' : record._module,
                    '__version': version,
                    '__attachments': attachment_dict_list
                })
            edi_dict_list.append(edi_dict)
            
        return edi_dict_list

    def edi_m2o(self, cr, uid, record, context=None):
        """Return a list representing a M2O EDI value for
           the given browse_record.
        M2O are passed as pair (ID, Name)
        Exmaple: ['db-uuid:xml-id',  'Partner Name']
        """
        # generic implementation!
        db_uuid = self.edi_xml_id(cr, uid, record, context=context)
        relation_model_pool = self.pool.get(record._name)  
        name = relation_model_pool.name_get(cr, uid, [record.id], context=context)
        name = name and name[0][1] or False
        return [db_uuid, name]
        
    def edi_o2m(self, cr, uid, records, edi_struct=None, context=None):
        """Return a list representing a O2M EDI value for
           the browse_records from the given browse_record_list.

        Example:
         [                                # O2M fields would be a list of dicts, with their
           { '__id': 'db-uuid:xml-id',    # own __id.
             '__last_update': 'iso date', # The update date, just in case...
             'name': 'some name',
             ...
           }],
        """
        # generic implementation!
        dict_list = []
        if context is None:
            context = {}
        ctx = context.copy()
        ctx.update({'o2m_export':True})
        for record in records:
            
            model_obj = self.pool.get(record._name)
            dict_list += model_obj.edi_export(cr, uid, [record], edi_struct=edi_struct, context=ctx)
        
        return dict_list
        
    def edi_m2m(self, cr, uid, records, context=None):
        """Return a list representing a M2M EDI value for
           the browse_records from the given browse_record_list.

        Example: 
        'related_tasks': [                 # M2M fields would exported as a list of pairs,
                  ['db-uuid:xml-id1',      # similar to a list of M2O values.
                   'Task 01: bla bla'],
                  ['db-uuid:xml-id2',
                   'Task 02: bla bla']
            ]
        """
        # generic implementation!
        dict_list = []
        
        for record in records:
            dict_list.append(self.edi_m2o(cr, uid, record, context=None))
      
        return dict_list

    def edi_export(self, cr, uid, records, edi_struct=None, context=None):
        """Returns a list of dicts representing an edi.document containing the
           browse_records with ``ids``, using the generic algorithm.
           :param edi_struct: if provided, edi_struct should be a dictionary
                              with a skeleton of the OSV fields to export as edi.
                              Basic fields can have any key as value, but o2m
                              values should have a sample skeleton dict as value.
                              For example, for a res.partner record:
                              edi_struct: {
                                   'name': True,
                                   'company_id': True,
                                   'address': {
                                       'name': True,
                                       'street': True,
                                   }
                              }
                              Any field not specified in the edi_struct will not
                              be included in the exported data.
        """
        # generic implementation!
        
        if context is None:
            context = {}
        if edi_struct is None:
            edi_struct = {}
        _columns = self._all_columns
        fields_to_export = edi_struct and edi_struct.keys() or _columns.keys()
        edi_dict_list = []
        value = None
        for row in records:
            edi_dict = {}
            edi_dict.update(self.edi_metadata(cr, uid, [row], context=context)[0])
            for field in fields_to_export:
                _column = _columns[field].column
                _column_dict = fields.field_to_dict(self, cr, uid, context, _column)
                record = getattr(row, field)
                if not record:
                    continue
                #if _fields[field].has_key('function') or _fields[field].has_key('related_columns'):
                #    # Do not Export Function Fields and related fields
                #    continue
                elif _column_dict['type'] == 'many2one':
                    value = self.edi_m2o(cr, uid, record, context=context)
                elif _column_dict['type'] == 'many2many':
                    value = self.edi_m2m(cr, uid, record, context=context)
                elif _column_dict['type'] == 'one2many':
                    value = self.edi_o2m(cr, uid, record, edi_struct=edi_struct.get(field, {}), context=context )
                else:
                    value = record
                edi_dict[field] = value
            edi_dict_list.append(edi_dict)
        return edi_dict_list


    def edi_get_object_by_name(self, cr, uid, value, model_name, context=None):
        openobject = False
        model = self.pool.get(model_name)
        object_ids = model.name_search(cr, uid, value, operator='=', context=context)
        if object_ids and len(object_ids) == 1:
            object_id = object_ids[0][0]
            openobject = model.browse(cr, uid, object_id, context=context)
        return openobject

    def edi_get_object(self, cr, uid, xml_id, model, context=None):
        model_data = self.pool.get('ir.model.data')
        module, xml_id2 = split_xml_id(xml_id)
        openobject = False
        data_ids = model_data.search(cr, uid, [('model','=', model), ('name','=', xml_id2)])
        if data_ids:
            model = self.pool.get(model)
            data = model_data.browse(cr, uid, data_ids[0], context=context)
            openobject = model.browse(cr, uid, data.res_id, context=context)
        return openobject

    def edi_create_relation(self, cr, uid, relation_model, relation_value, context=None):
        relation_model = self.pool.get(relation_model)
        values = {} #relation_model.default_get(cr, uid, fields, context=context)
        values[relation_model._rec_name] = relation_value            
        return relation_model.create(cr, uid, values, context=context)

    def edi_import_relation(self, cr, uid, relation_model, relation_value, xml_id=None, context=None):
        relation = False
        if xml_id:
            relation = self.edi_get_object(cr, uid, xml_id, relation_model, context=context)
        if not relation:
            relation = self.edi_get_object_by_name(cr, uid, relation_value, relation_model, context=context)
        if not relation:
            relation_id = self.edi_create_relation(cr, uid, relation_model, relation_value, context=context)
            relation = relation_model.browse(cr, uid, relation_id, context=context)

        record_xml = self.record_xml_id(cr, uid, relation, context=context)
        if record_xml:
            module, xml_id = record_xml
            xml_id = '%s.%s' % (module, xml_id)
        if not xml_id:
            xml_id = self.edi_xml_id(cr, uid, relation, context=context)
        
        #TODO: update record from values ?
        #relation_id = model_data._update(cr, uid, relation_model, module, values, xml_id=xml_id, context=context)
        return relation and relation.id or False
        
    def edi_import(self, cr, uid, edi_document, context=None):
    
        """Imports a list of dicts representing an edi.document, using the
           generic algorithm.

             All relationship fields are exported in a special way, and provide their own
             unique identifier, so that we can avoid duplication of records when importing.
             Note: for all ir.model.data entries, the "module" value to use for read/write
                   should always be "edi_import", and the "name" value should be the full
                   db_id provided in the EDI.

             1: Many2One
             M2O fields are always exported as a pair [db_id, name], where db_id
             is in the form "db_uuid:xml_id", both being values that come directly
             from the original database.
             The import should behave like this:
                 a. Look in ir.model.data for a record that matches the db_id.
                    If found, replace the m2o value with the correct database ID and stop.
                    If not found, continue to next step.
                 b. Perform name_search(name) to look for a record that matches the
                    given m2o name. If only one record is found, create the missing
                    ir.model.data record to link it to the db_id, and the replace the m2o
                    value with the correct database ID, then stop. If zero result or
                    multiple results are found, go to next step.
                 c. Create the new record using the only field value that is known: the
                    name, and create the ir.model.data entry to map to it.
                    This should work for many models, and if not, the module should
                    provide a custom EDI import logic to care for it.

             2: One2Many
             O2M fields are always exported as a list of dicts, where each dict corresponds
             to a full EDI record. The import should not update existing records
             if they already exist, it should only link them to the parent object.
                 a. Look for a record that matches the db_id provided in the __id field. If
                    found, keep the corresponding database id, and connect it to the parent
                    using a write value like (4,db_id).
                 b. If not found via db_id, create a new entry using the same method that
                    imports a full EDI record (recursive call!), grab the resulting db id,
                    and use it to connect to the parent via a write value like (4, db_id).

             3: Many2Many
             M2M fields are always exported as a list of pairs similar to M2O.
             For each pair in the M2M:
                 a. Perform the same steps as for a Many2One (see 1.2.1.1)
                 b. After finding the database ID of the final record in the database,
                    connect it to the parent record via a write value like (4, db_id).        
        """
        # generic implementation!
        model_data = self.pool.get('ir.model.data')
        assert self._name == edi_document['__model'], 'EDI Document could not import. Model of EDI Document and current model are does not match'
        def process(datas, model_name):
            values = {}
            model_pool = self.pool.get(model_name)
            xml_id = datas['__id']
            module, xml_id2 = split_xml_id(xml_id)
            _columns = model_pool._all_columns
            for field in datas.keys():
                if field not in _columns:
                    continue
                if not field.startswith('__'):
                    _column = _columns[field].column
                    _column_dict = fields.field_to_dict(self, cr, uid, context, _column)
                
                    edi_field_value = datas[field]
                    field_type = _column_dict['type']
                    relation_model = _column_dict.get('relation')
                    if not edi_field_value:
                        continue
                    if _column_dict.has_key('function') or _column_dict.has_key('related_columns'):
                        # DO NOT IMPORT FUNCTION FIELD AND RELATED FIELD
                        continue
                    elif field_type == 'one2many':
                        # recursive call for getting children and returning [(0,0,{})] or [(1,ID,{})]
                        relations = []
                        relation_object = self.pool.get(relation_model)
                        for edi_relation_document in edi_field_value:
                            relation = self.edi_get_object(cr, uid, edi_relation_document['__id'], relation_model, context=context)
                            if not relation and edi_relation_document.get('name'):
                                relation = self.edi_get_object_by_name(cr, uid, edi_relation_document['name'], relation_model, context=context)
                            if relation:
                                self.edi_xml_id(cr, uid, relation, \
                                                    xml_id=edi_relation_document['__id'], context=context)
                                relations.append((4, relation.id))
                            res_module, res_xml_id, newrow = process(edi_relation_document, relation_model)
                            relations.append( (relation and 1 or 0, relation and relation.id or 0, newrow))
                        values[field] = relations
                    elif field_type in ('many2one', 'many2many'):
                        if field_type == 'many2one':
                            edi_parent_documents = [edi_field_value]
                        else:
                            edi_parent_documents = edi_field_value

                        parent_lines = []

                        for edi_parent_document in edi_parent_documents:
                            relation_id = self.edi_import_relation(cr, uid, relation_model, edi_parent_document[1], edi_parent_document[0], context=context)
                            parent_lines.append(relation_id)
                            
                        if len(parent_lines):   
                            if field_type == 'many2one':
                                values[field] = parent_lines[0]
                                
                            else:
                                many2many_ids = []
                                for m2m_id in parent_lines:
                                    many2many_ids.append((4, m2m_id))
                                values[field] = many2many_ids
                    
                    else:
                        values[field] = edi_field_value
            return module, xml_id2, values
        
        module, xml_id, data_values = process(edi_document, self._name)
        return model_data._update(cr, uid, self._name, module, data_values, xml_id=xml_id, context=context)
# vim: ts=4 sts=4 sw=4 si et
