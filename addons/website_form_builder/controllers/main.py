# -*- coding: utf-8 -*-
import base64

import json
import collections

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _
from pprint import pprint

class contactus(http.Controller):
    
    def print_r(self,title, iterable):
        print "\n%s\n________________________________________________\n\n" %title
        if isinstance(iterable,dict):
            for field_name, field_value in iterable.items():
                print "%s \t : %s\n" % (field_name, field_value)
            
        else: 
            i = 0
            for field in iterable:
                print "[%i]\t : %s\n" % (i, field)
                i += 1
                
        print "\n\n"
            
              
    def __init__(self):
        
        self.filter = {'char': self.char, 'text': self.text, 'many2one': self.many2one, 
                       'one2many': self.one2many, 'many2many':self.many2many, 'selection': self.selection, 
                       'boolean': self.boolean,'integer': self.integer,'float': self.float}

        #_TECHNICAL = ['show_info', 'view_from', 'view_callback']  # Only use for behavior, don't stock it
        #_BLACKLIST = ['id', 'create_uid', 'create_date', 'write_uid', 'write_date', 'user_id', 'active']  # Allow in description
        #_REQUIRED = ['name', 'contact_name', 'email_from', 'description']  # Could be improved including required from model
    
    # List of filters following type of field to be fault tolerent
    
    def char(self,label,input):
        return input
    
    def text(self,label,input):
        return input
    
    def many2one(self,label,input):
        return int(input or 0)
    
    def one2many(self,label,input):
        print input
        output = []
        for elem in input:
            output.append(int(elem or 0))     
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
        
        # self.print_r("Authorized columns", request.registry[self._model]._all_columns)
        
        for field_name, field_value in kwargs.items():  
              
            if hasattr(field_value, 'filename'):
                self._files.append(field_value)
                
            elif field_name in request.registry[self._model]._all_columns and field_name not in self._BLACKLIST:
                type = request.registry[self._model]._all_columns[field_name].column._type;
                self._post[field_name] = self.filter[type](field_name,field_value);
                
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
            print 'Attachment', request.registry['ir.attachment'].create(request.cr, SUPERUSER_ID, attachment_value, context=request.context)  
        
    def checkModel(self,model):
        if model in self._MODEL_WHITE_LIST:
            self._model = model
            return True      
        else: 
            return False
     
    def insert(self):     
        values = self._post;
        values['description'] += "\n\n" + self._custom + "\n\n" + self._meta
        self.print_r("Values Inserted", values)
        
        return request.registry[self._model].create(request.cr, SUPERUSER_ID, values, request.context);
        
    def authorized_fields(self):
        request.registry['website.form'].get_authorized_fields(request.cr, SUPERUSER_ID, self._model)
        
    @http.route('/contactus_success', type='http', auth="public", website=True)
    def success(self, **kwargs):
         return request.website.render("website_form_builder.contactus_success")
     
    @http.route('/contactus_fail', type='http', auth="public", website=True)
    def fail(self, **kwargs):
         return request.website.render("website_form_builder.contactus_fail") 
     
    @http.route('/contactus/<model>', type='json', auth="public", website=True)     
    def contactus(self,model, **kwargs):
        
        self._MODEL_WHITE_LIST = []

        self._TECHNICAL = []
             
        self._model     = "" #'crm.lead'
        self._files     = [] # List of attached files
        self._post      = {} # Dict of values to create entry on the model
        self._custom    = "Custom infos \n________________________________________________\n\n" # Extra data from custom fields
        self._meta      = "Metadata     \n________________________________________________\n\n"     # meta data
        self._request   = None
        self.error      = None
        self._request = request
        
        self._MODEL_WHITE_LIST = request.registry['website.form'].get_authorized_models(request.cr, SUPERUSER_ID)
        
        if not self.checkModel(model) :
            return False
        
        self._BLACKLIST = request.registry['website.form'].get_blacklist(request.cr, SUPERUSER_ID, self._model)
        self._REQUIRED = request.registry['website.form'].get_required_fields(request.cr, SUPERUSER_ID, self._model)
        print 'required : ', self._REQUIRED
        self.extractData(**kwargs) 
        
        self.print_r("POST", self._post)
        self.print_r("Files", self._files)
        
        print "\n\n %s \n\n %s \n\n" %(self._custom, self._meta)
       
        self.print_r("Error", self.error)
        try:     
            if(any(self.error)) :   id = 0
            else :                  id = self.insert()
        except:
            id = 0
        
        
        if id: 
            self.linkAttachment(id)
        
        print self.error
        
        return self.error and {'id': id, 'fail_required' : self.error} or {'id': id, 'fail_required': None} 
