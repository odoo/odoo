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
import json
import hashlib
import time
import base64
import urllib2

def safe_unique_id(model, database_id):
    """Generate a unique string to represent a (model,database id) pair
    without being too long, without revealing the database id, and
    with a very low probability of collisions.

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
    msg = "%s-%s-%s" % (model, time.time(), database_id)
    digest = hashlib.sha1(msg).digest()
    digest = ''.join(chr(ord(x) ^ ord(y)) for (x,y) in zip(digest[:9], digest[9:-2]))
    # finally, use the b64-encoded folded digest as ID part of the unique ID:
    digest = base64.urlsafe_b64encode(digest)
        
    return '%s-%s' % (model,digest)

class ir_edi_document(osv.osv):
    _name = 'ir.edi.document'
    _description = 'To represent the EDI export of any OpenERP record, it could be an invoice, a project task, etc.
    _columns = {
                'name': fields.char("EDI token", size = 128, help="EDI Token is a unique identifier for the EDI document."),
                'document': fields.text("Document", help="hold the serialization of the EDI document.")
                
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The EDI Token must be unique!')
    ]
    
    
    def new_edi_token(self, record):
        """
        Return a new, random unique token to identify an edi.document
        :param record: It's a object of browse_record of any model
        """
        db_uuid = safe_unique_id(record._name, record.id)
        edi_token = hashlib.sha256('%s-%s-%s' % (time.time(), db_uuid, time.time())).hexdigest()
        return edi_token
    
    def serialize(self, edi_documents):
        """Serialize the list of dictionaries using json dumps method
        perform a JSON serialization of a list of dicts prepared by generate_edi() and return a UTF-8 encoded string that could be passed to deserialize()
        :param edi_dicts: it's list of edi_dict
        """
        serialized_list = json.dumps(edi_dicts)
        return serialized_list
    
    def generate_edi(self, cr, uid, records, context=None):
        """
        Generate the list of dictionaries using edi_export method of edi class 
        :param records: it's a object of browse_record_list of any model
        """
        edi_list = []
        for record in record_list:
            edi_struct = record.edi_export(cr, uid, record, context=context)
            edi_list.append(edi_struct)
        return self.serialize(edi_list)
    
    def get_document(self, cr, uid, edi_token, context=None):
        """
        Get the edi document from database using given edi token 
        returns the string serialization that is in the database (column: document) for the given edi_token or raise.
        """
        
        records = self.name_search(cr, uid, edi_token, context=context)
        if records:
            edi = self.browse(cr, uid, records[0], context=context)
            return edi.document
        else:
            raise osv.except_osv(_('Error !'),
                _('Desired EDI Document does not Exist'))  
        
        
    
    def load_edi(self, cr, uid, edi_documents, context=None):
        """
        loads the values from list of dictionaries to the corresponding OpenERP records
        using the edi_import method of edi class
        For each edi record (dict) in the list, call the corresponding osv.edi_import() method, based on the __model attribute (see section 2.4 of  for spec of 
        osv.edi_import)

        :param edi_dicts: list of edi_dict
        """
       
        for edi_document in edi_documents:
            model = edi_document.get('__model')
            assert model, _('model should be provided in EDI Dict')
            model_obj = self.pool.get(model)
            model_obj.edi_import(cr, uid, edi_document, context=context)
        return True
    
    def deserialize(self, edi_document_string):
        """ Deserialized the edi document string
        perform JSON deserialization from an edi document string, and returns a list of dicts
        """
        edi_document = json.loads(edi_document_string)
        return edi_document
    
    def export(self, cr, uid, records, context=None):
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
            token = self.new_edi_token(record)
            self.create(cr, uid, {
                         'name': token,
                         'document': document
                        }, context=context)
        
            exported_ids.append(token)
        return exported_ids
    
    def import(self, cr, uid, edi_document=None, edi_url=None, context=None):
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
        # generic implementation!
        attachment_object = self.pool.get('ir.attachment')
        edi_dict_list = []
        for record in records:
            attachment_ids = attachment_object.search(cr, uid, [('res_model','=', record._name), ('res_id', '=', record.id)])
            attachment_dict_list = []
            for attachment in attachment_object.browse(cr, uid, attachment_ids, context=context):
                attachment_dict_list.append({
                        'name' : attachment.name,
                        'content': base64.encodestring(attachment.datas),
                        'file_name': attachment.datas_fname,
                })
            edi_dict = {
                '__model' : record._name,
                '__module' : record._module,
                '__id': record.id,
                '__last_update': record.write_date, #TODO: convert into UTC
                '__version': [], # ?
                '__attachments': attachment_dict_list
            }
            edi_dict_list.append(edi_dict)
            
        return edi_dict_list

    def edi_m2o(self, cr, uid, record, context=None):
        """Return a list representing a M2O EDI value for
           the given browse_record.
        M2O are passed as pair (ID, Name)
        Exmaple: ['db-uuid:xml-id',  'Partner Name']
        """
        # generic implementation!
        data_object = self.pool.get('ir.model.data')
        db_uuid = safe_unique_id(record._name, record.id)
        xml_ids = data_object.search(cr, uid, [('model','=',record._name),('res_id','=',record.id)])
        if xml_ids:
            xml_id = data_object.browse(cr, uid, xml_ids[0], context=context)
            xml_id = xml_id.name
            db_uuid = '%s:%s' %(db_uuid, xml_id)
        name = record.name
        return [db_uuid, name]
        

    def edi_o2m(self, cr, uid, records, context=None):
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
        for record in records:
            model_obj = self.pool.get(record._name)
            dict_list += model_obj.edi_export(cr, uid, [record.id], context=context)
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
            dict_list.append(self.edi_o2m(cr, uid, record, context=None))
           
        return dict_list

    def edi_export(self, cr, uid, ids, edi_struct=None, context=None):
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
        
        self.edi_document = {
                      
                      '__model':'',
                      '__module':'',
                      '__id':'',
                      '__last_update':'',
                      '__version':'',
                      '__attachments':'',
                      
                      }
        self.edi_document['__model'] = self._name
        
        
        fields_object = self.pool.get('ir.model.fields')
        model_object = self.pool.get(self.edi_document['__model'])
        edi_metadata(cr, uid, edi_struct, context=context)
        record = model_object.read(cr,uid,ids,[],context=context)
        for field in edi_struct.keys():
            f_ids = fields_object.search(cr,uid,[('name','=',field),('model','=',self.edi_document['__model'])],context=context)
            
            for fname in fields_object.browse(cr,uid,f_ids):
                if fname.ttype == 'many2one':
                    
                    self.edi_document[field] = self.edi_m2o(cr, uid, browse_rec = record[0][field])
                elif fname.ttype == 'one2many':
                    
                    self.edi_ducument[field] = self.edi_o2m(cr,uid,line = edi_struct[field],browse_rec_list = record[0][field])
                elif fname.ttype == 'many2many':        
                    self.edi_document[field] = self.edi_m2m(cr,uid,line = edi_struct[field],browse_rec_list = record[0][field])
                else:
                    self.edi_document[field] = record[0][field]
        
            
        return self.edi_document
    def determine_type(self,cr,uid,ids,record_line,browse_record=None,context=None):
        model = browse_record._name
        fields_object = self.pool.get('ir.model.fields')
        obj = self.pool.get(model)
        field_data = obj.read(cr,uid,browse_record.id,record_line.keys())[0]
        for field in field_data.keys():
            field_ids = field_object.search(cr,uid,[field])
            for field_type in field_object.browse(cr,uid,field_ids): 
                if field_type.ttype == 'many2one':
                    record_line.update(field,self.edi_m2o(cr,uid,browse_rec = field_data[field]))
                elif field_type.ttype == 'one2many':
                    pass
                elif field_type.ttype == 'many2many':
                    pass
                else:
                    record_line.update(field,field_data[field])
        return record_line
        
    def edi_import(self, cr, uid, edi_document, context=None):
    
        """Imports a list of dicts representing an edi.document, using the
           generic algorithm.
        """
        # generic implementation!
        new = True
        resource = {}
        model = edi_document['__model']
        model_object = self.pool.get(model)
        data_model = self.pool.get('ir.model.data')
        field_model = self.pool.get('ir.model.fields')
        for field in edi_document.keys():
            if field == '__id':
                db_id , xml_ID = edi_document[field].split(':')
                self.data_ids = data_model.search(cr,uid,[('name','=',xml_ID)])
            
               
            f_ids = fields_object.search(cr,uid,[('name','=',field),('model','=',model)],context=context)
            for fname in fields_object.browse(cr,uid,f_ids):
                
                if fname.ttype == 'many2one':
                    field_ids,field_xml = edi_document[field][0].split(':')
                    field_ids = int(field_ids)
                    model_ids = data_model.search(cr,uid,[('name','=',field_xml)])
                    if not len(model_ids):
                        obj = self.pool.get(fname.relation)
                        model1_ids = obj.search(cr,uid,[('name','=',edi_document[field][1])])
                        if len(model1_ids) == 1:
                            resourse[field] = data_model.create(cr,uid,{'module':'edi_import','name':field_xml,'res_id':model1_ids})[0]
                          
                        elif not len(model1_ids) or len(model1_ids) > 1:
                            edi_document[field][1] = obj.create(cr,uid,{'name':edi_document[field][1]})
                            resource[field] = data_model.create(cr,uid,{'module':'edi_import','name':field_xml,'res_id':edi_document[field][0]})[0]   
                    else:
                        resource[field] = model_ids[0]
                                
                elif fname.ttype == 'one2many':
                    for records in edi_document[field]:
                        res = {}
                        field_ids,field_xml = records['__id'].split(':')
                        field_ids = int(field_ids)
                        model3_ids = data_model.search(cr,uid,[('name','=',field_xml)])
                        for fields in records.keys():
                            if fields != '__id' or fields != '__last_update':
                                res[fields] = records[fields]
                        if not len(model3_ids):
                            resource[field][records] = (4,self.edi_import(cr,uid,res,context = context)[0])
                        else:
                            resource[field][records] = (4,model3_ids[0])obj = self.pool.get(model)
                record_ids = obj.create(cr,uid,resource,context=context)
                return record_ids
                        
                elif fname.ttype == 'many2many':        
                    for records in edi_document[field]:
                        field_ids,field_xml = records[0].split(':')
                        field_ids = int(field_ids)
                        model4_ids = data_model.search(cr,uid,[('name','=',field_xml)])
                        if not len(model4_ids):
                            obj = self.pool.get(fname.relation)
                            name,value = records[1].split(':')
                            model5_ids = obj.search(cr,uid,[(name,'=',value)])
                            if len(model5_ids) == 1:
                                resource[field][records] = data_model.create(cr,uid,{'module':'edi_import','name':field_xml,'res_id':model5_ids})[0]
                            elif not len(model5_ids) or len(model5_ids) > 1:
                                edi_document[field][records][1] = obj.create(cr,uid,{'name':edi_document[field][1]})
                                resource[field] = (4,data_model.create(cr,uid,{'module':'edi_import','name':field_xml,'res_id':edi_document[field][records][1]})[0])  
                        else:
                            resource[field] = (4,model4_ids[0])
                else:
                    resource[field] = edi_document[field]
        if len(self.data_ids):
            obj = self.pool.get(model)
            record_ids = obj.write(cr,uid,resource,context=context)
            return record_ids
        else:
            obj = self.pool.get(model)
            record_ids = obj.create(cr,uid,resource,context=context)
            return record_ids
