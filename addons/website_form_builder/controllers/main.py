# -*- coding: utf-8 -*-
import base64

import json
import collections

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _

class contactus(http.Controller):
              
    def __init__(self):
        
        self.filter = {'char': self.char, 'text': self.text, 'many2one': self.many2one, 
                       'one2many': self.one2many, 'many2many':self.many2many, 'selection': self.selection, 
                       'boolean': self.boolean,'integer': self.integer,'float': self.float}
    
    # List of filters following type of field to be fault tolerent
    def get_int(self,x):
        return int(''.join(ele for ele in x if ele.isdigit()))

    def get_float(self,x):
        return float(''.join(ele for ele in x if ele.isdigit() or ele == '.'))

    def char(self, label, input):
        return input
    
    def text(self, label, input):
        return input
    
    def many2one(self, label, input):
        return int(self.get_int(input) or 0)
    
    def one2many(self, label, input):
        output = []
        input = input.split(',')
        for elem in input:
            input_int = int(self.get_int(elem) or 0)
            if input_int :
                output.append(input_int)     
        return output
    
    def many2many(self, label, input, *args):
        op = (6,0)
        if len(args) == 1: op = args[0]
        output = self.one2many(label,input)
        return [op + (output,)]
    
    def selection(self, label, input):
        return int(self.get_int(input) or 0)
    
    def boolean(self, label, input):
        return (input != 0)
    
    def integer(self, label, input):
        return int(self.get_int(input) or 0)
    
    def float(self, label, input):
        return float(self.get_float(input) or 0)

    # Extract all data sent by the form and sort its on several properties
    def extractData(self, **kwargs):
        print kwargs
        for field_name, field_value in kwargs.items():  
            print field_name, ' : ', field_value, '\n'
            if hasattr(field_value, 'filename'):
                field_value.field_name = field_name
                self._files.append(field_value)
                
            elif field_name in request.registry[self._model]._all_columns and field_name not in self._BLACKLIST:
                type = request.registry[self._model]._all_columns[field_name].column._type;
                field_filtered = self.filter[type](field_name,field_value);
                if field_filtered: self._post[field_name] = field_filtered
                
            elif field_name not in self._TECHNICAL:
                self._custom += "%s : %s\n" % (field_name, field_value)
                
                
        environ = request.httprequest.headers.environ 
        
        self._meta += "%s : %s\n%s : %s\n%s : %s\n%s : %s\n" % ("IP"                , environ.get("REMOTE_ADDR"), 
                                                                "USER_AGENT"        , environ.get("HTTP_USER_AGENT"),
                                                                "ACCEPT_LANGUAGE"   , environ.get("HTTP_ACCEPT_LANGUAGE"),
                                                                "REFERER"           , environ.get("HTTP_REFERER"))
        
        self.error = list(set(field for field in self._REQUIRED if not self._post.get(field)))
        
        return any(self.error)
    
    # Link all files attached on the form
    def linkAttachment(self,id_record):
        
        for file in self._files:
            file.field_name = file.field_name.split('[')[0]
            print file.field_name, '\n'
            attachment_value = {
                'name': file.filename,
                'res_name': file.filename,
                'res_model': self._model,
                'res_id': id_record,
                'datas': base64.encodestring(file.read()),
                'datas_fname': file.filename,
            }
            id_a = request.registry['ir.attachment'].create(request.cr, SUPERUSER_ID, attachment_value, context=request.context)  
            if file.field_name in request.registry[self._model]._all_columns and file.field_name not in self._BLACKLIST:
                type = request.registry[self._model]._all_columns[file.field_name].column._type;
                values = {}
                values[file.field_name] = self.filter[type](file.field_name, str(id_a), (4,));
                print 'update file list : - id_attachment :', id_a, '; id_message : ', id_record, ' value: ', values
                print 'reponse : ', request.registry[self._model].write(request.cr, SUPERUSER_ID, [id_record], values, request.context);
        
     
    def insert(self):
        values = self._post;
        if self.field not in values : values[self.field] = ''
        values[self.field] += "\n\n" + self._custom + "\n\n" + self._meta
        print 'INSERT :: ', values
        return request.registry[self._model].create(request.cr, SUPERUSER_ID, values, request.context);
        
    def authorized_fields(self):
        request.registry['website.form'].get_authorized_fields(request.cr, SUPERUSER_ID, self._model)
    
    @http.route('/page/website.form.thankyou', type='http', auth="public", website=True)
    def form_thankyou(self):
        return request.website.render("website_form_builder.form_thankyou")

    @http.route('/page/website.form.error', type='http', auth="public", website=True)
    def form_error(self):
        return request.website.render("website_form_builder.form_error")


    @http.route('/website_form/<model>', type='http', auth="public", website=True)
    def contactus(self,model, **kwargs):

        obj_form = request.registry['website.form']

        self._MODEL_WHITE_LIST = []

        self._TECHNICAL = ['context']
             
        
        self._files     = [] # List of attached files
        self._post      = {} # Dict of values to create entry on the model
        self._custom    = "Custom infos \n________________________________________________\n\n" # Extra data from custom fields
        self._meta      = "Metadata     \n________________________________________________\n\n"     # meta data
        self.error      = None
        self._request   = request
        id_model        = obj_form.search(request.cr,SUPERUSER_ID,[('model_id', '=', model),],context=request.context)
        if not id_model: #if not authorized model
            return request.website.render("website_form_builder.xmlresponse",{'response':False})
        
        self._model     = model 

        print "authorized model \n\n"
            # return all meta-fields of the selected model

        formModel = obj_form.browse(request.cr, SUPERUSER_ID, id_model)

        self.field      = formModel.metadata_field_id.name;
        self._BLACKLIST = [field.name for field in formModel.blacklist_field_ids]
        self._REQUIRED  = obj_form.get_required(request.cr, SUPERUSER_ID, self._model)

        self.extractData(**kwargs) 
        
        print "error : ", self.error, "\n\n"
        try:     
            if(any(self.error)) :   id_record = 0
            else :                  id_record = self.insert()
        except ValueError:
            print ValueError
            id_record = 0
        
        
        if id_record: 
            self.linkAttachment(id_record)

        if self.error : 
            response = json.dumps({'id': id_record, 'fail_required' : self.error});
        else : 
            response = json.dumps({'id': id_record, 'fail_required': None});

        return request.website.render("website_form_builder.xmlresponse",{'response':response})
