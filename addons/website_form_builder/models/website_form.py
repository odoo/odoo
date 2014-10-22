# -*- coding: utf-8 -*-

import urlparse
from openerp.http import request
from openerp.osv import fields, osv


class website_form(osv.Model):
    """ Manage models, blacklists, etc.. for form builder"""
    _name = 'website.form'

    _columns = {
        'model'                 : fields.char("Model"),
        'blacklist_field_ids'   : fields.many2many('ir.model.fields',string='Black List'),
        'name'                  : fields.text("Label for Model Selection",translate=True),
        'metadata_field_ref'    : fields.text("Specify the field wich will contain meta and custom datas"),
    }
    _defaults = {
        'blacklist_field_ids': [],
        'metadata_field_ref': 'description',
    }
    
    # return partner id and create it if not exist
    def insert_partner(self, cr, uid, email, context=None):
        id = self.pool['res.partner'].search(cr,uid, [('email', '=', email),], limit=1, context=context)
        if not id:
            id = self.pool['res.partner'].create(cr, uid, {'email': email, 'name': email}, context=context)
        return id
    
    # return all partners
    def get_partners(self, cr, uid, search, context=None):
        output = []
        ids = self.pool['res.partner'].search(cr, uid, [('email', '=like', search+'%'),],limit=5, context=context)
        for elem in self.pool['res.partner'].browse(cr,uid,ids):
            output.append(elem.email)
        return output
     
    # return the model name and the label option for the drag n drop wizard
    def get_options_list(self, cr, uid, context=None):
        output = []
        ids = self.search(cr, uid, [], context=context)
        for elem in self.browse(cr, uid, ids):
            output.append({'model': elem.model, 'name': elem.name})
        return output
    
    # return all meta-fields of the selected model
    def get_model_infos(self, cr, uid, model, context=None):
        id = self.search(cr, uid, [('model', '=', model),],limit=1, context=context)
        return self.browse(cr, uid, id)

    # return a list of blacklisted fields
    def get_blacklist(self, cr, uid, model, context=None):
        id = self.search(cr, uid, [('model', '=', model),],limit=1, context=context)
        return [field.name for field in self.browse(cr, uid, id).blacklist_field_ids]
    
    # filter all fields to get all authorized fields            
    def get_authorized_fields(self, cr, uid, model, context=None):
        print 'get authorizeed fields \n'
        output = self.pool[model].fields_get(cr,uid,context=context)
        for elem in self.get_blacklist(cr, uid, model, context=context):
            output.pop(elem, None)
        for key, val in self.pool[model]._inherits.iteritems():
            output.pop(val,None)
        for key, val in output.iteritems():
            if 'relation' in val and val['relation'] == 'ir.attachment':
                print val['type']
                val['type'] = 'binary'


        return output
        
    # get all required fields from field model
    def get_required(self, cr, uid, model, context=None):
        output = []
        filter = [('model', '=', model),('required','=',True),]  
        ids = self.pool['ir.model.fields'].search(cr,uid,filter,context=context)
        for elem in self.pool['ir.model.fields'].browse(cr,uid,ids):
            output.append(elem.name)
        for key, val in self.pool[model]._inherits.iteritems():
            if val in output:
                output.remove(val)
        return output
    
    def is_authorized_model(self, cr, uid, model, context=None):
        result = self.search(cr,uid,[('model', '=', model),],context=context)
        print "\n\n\n is Authorized Model : ",model, " :: ", result
        return result
