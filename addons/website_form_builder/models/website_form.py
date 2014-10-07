# -*- coding: utf-8 -*-

import urlparse

from openerp.http import request
from openerp.osv import fields, osv


class website_form(osv.Model):
    """ Manage models, blacklists, etc.. for form builder"""
    _name = 'website.form'

    _columns = {
        'model': fields.char("Model"),
        'blacklist_field_ids': fields.many2many('ir.model.fields',string='Black List'),
        'label_option' : fields.text("Label for Model Selection",translate=True),
    }
    _defaults = {
        'blacklist_field_ids': [],
    }
    
    # return partner id and create it if not exist
    def insert_partner(self, cr, uid, email, context=None):
        list = []
        id = self.pool['res.partner'].search(cr,uid, [('email', '=', email),], limit=1, context=context)
        if not id:
            id = self.pool['res.partner'].create(cr, uid, {'email': email, 'name': email}, context=context)
        return id
    
    # return all partners
    def get_partners(self, cr, uid, context=None):
        list = []
        ids = self.pool['res.partner'].search(cr, uid, [], context=context)
        for elem in self.pool['res.partner'].browse(cr,uid,ids):
            list.append(elem.email)
        return list
     
    # return the model name and the label option for the drag n drop wizard
    def get_options_list(self, cr, uid, context=None):
        list = []
        ids = self.search(cr, uid, [], context=context)
        for elem in self.browse(cr, uid, ids):
            list.append({'model': elem.model, 'label_option': elem.label_option})
        return list
    
    # return a list 
    def _get_blacklist_fields(self, cr, uid, model, context=None):
        id = self.search(cr, uid, [('model', '=', model),],limit=1, context=context)
        return self.browse(cr, uid, id).blacklist_field_ids
    
    # return a list of blacklisted fields
    def get_blacklist(self,cr,uid,model,context=None):
        list = []
        for elem in self._get_blacklist_fields(cr, uid, model, context=context):
            list.append(elem.name);
        return list
    
    # filter all fields to get all authorized fields            
    def get_authorized_fields(self, cr, uid, model, context=None):
        list = self.pool[model].fields_get(cr,uid,context=context)
        for elem in self._get_blacklist_fields(cr, uid, model, context=context):
            list.pop(elem.name, None)
        for key, val in self.pool[model]._inherits.iteritems():
            list.pop(val,None)
        return list
        
    # get all required fields from field model
    def get_required_fields(self, cr, uid, model, context=None):
        list = []
        filter = [('model', '=', model),('required','=',True),]  
        ids = self.pool['ir.model.fields'].search(cr,uid,filter,context=context)
        for elem in self.pool['ir.model.fields'].browse(cr,uid,ids):
            list.append(elem.name)
        for key, val in self.pool[model]._inherits.iteritems():
            if val in list:
                list.remove(val)
        return list
    
    def get_authorized_models(self, cr, uid, context=None):
        list = []
        ids = self.search(cr,uid,[],context=context);
        for elem in self.browse(cr, uid,ids, context=context):
            list.append(elem.model)
        return list
    
    
    