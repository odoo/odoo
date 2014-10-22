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
    
    def char(self,label,input):
        return input
    
    def text(self,label,input):
        return input
    
    def many2one(self,label,input):
        return int(input or 0)
    
    def one2many(self,label,input):
        output = []
        input = input.split(',')
        for elem in input:
            input_int = int(elem or 0)
            if input_int :
                output.append(input_int)     
        return output
    
    def many2many(self,label,input):
        output = self.one2many(label,input)
        return [(6,0,output)]
    
    def selection(self,label,input):
        return int(input or 0)
    
    def boolean(self,label,input):
        return (input != 0)
    
    def integer(self,label,input):
        return int(input or 0)
    
    def float(self,label,input):
        return float(input or 0)

    # Extract all data sent by the form and sort its on several properties
    def extractData(self, **kwargs):
        print kwargs
        for field_name, field_value in kwargs.items():  
            print field_name, ' : ', field_value, '\n'
            if hasattr(field_value, 'filename'):
                self._files.append(field_value)
                
            elif field_name in request.registry[self._model]._all_columns and field_name not in self._BLACKLIST:
                type = request.registry[self._model]._all_columns[field_name].column._type;
                field_filtered = self.filter[type](field_name,field_value);
                if field_filtered: self._post[field_name] = field_filtered
                
            elif field_name not in self._TECHNICAL:
                self._custom += "%s : %s\n" % (field_name, self._request.httprequest.form.getlist(field_name))
                
                
        environ = request.httprequest.headers.environ 
        
        self._meta += "%s : %s\n%s : %s\n%s : %s\n%s : %s\n" % ("IP"                , environ.get("REMOTE_ADDR"), 
                                                                "USER_AGENT"        , environ.get("HTTP_USER_AGENT"),
                                                                "ACCEPT_LANGUAGE"   , environ.get("HTTP_ACCEPT_LANGUAGE"),
                                                                "REFERER"           , environ.get("HTTP_REFERER"))
        
        self.error = list(set(field for field in self._REQUIRED if not self._post.get(field)))
        
        return any(self.error)
    
    # Link all files attached on the form
    def linkAttachment(self,id):
        
        for file in self._files:
            attachment_value = {
                'name': file.filename,
                'res_name': file.filename,
                'res_model': self._model,
                'res_id': id,
                'datas': base64.encodestring(file.read()),
                'datas_fname': file.filename,
            }
            id_a = request.registry['ir.attachment'].create(request.cr, SUPERUSER_ID, attachment_value, context=request.context)  
            print attachment
        
     
    def insert(self):     
        values = self._post;
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
        
        if not obj_form.is_authorized_model(request.cr, SUPERUSER_ID, model) :
            return request.website.render("website_form_builder.xmlresponse",{'response':False})
        
        self._model     = model 

        print "authorized model \n\n"

        self.field      = obj_form.get_model_infos(request.cr, SUPERUSER_ID, self._model).metadata_field_ref
        self._BLACKLIST = obj_form.get_blacklist(request.cr, SUPERUSER_ID, self._model)
        self._REQUIRED  = obj_form.get_required(request.cr, SUPERUSER_ID, self._model)

        self.extractData(**kwargs) 
        
        print "error : ", self.error, "\n\n"
        try:     
            if(any(self.error)) :   id = 0
            else :                  id = self.insert()
        except:
            id = 0
        
        
        if id: 
            self.linkAttachment(id)

        if self.error : 
            response = json.dumps({'id': id, 'fail_required' : self.error});
        else : 
            response = json.dumps({'id': id, 'fail_required': None});

        return request.website.render("website_form_builder.xmlresponse",{'response':response})
