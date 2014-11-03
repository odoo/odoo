# -*- coding: utf-8 -*-

import urlparse
from openerp.http import request
from openerp.osv import fields, osv


class website_form(osv.Model):
    """ Manage models, blacklists, etc.. for form builder"""
    _name = 'website.form'

    _columns = {
        'model'                 : fields.many2one('ir.model','Model',ondelete='cascade'),
        'blacklist_field_ids'   : fields.many2many('ir.model.fields', string='Black List'),
        'name'                  : fields.char("Help Label", help="Label for Model Selection",translate=True),
        'metadata_field_ref'    : fields.many2one('ir.model.fields', 'Default Field', ondelete='cascade', help="Specify the field wich will contain meta and custom datas"),
        'model_name'            : fields.related('model','model',type="char",string="Model reference", readonly=True),
    }
    _defaults = {
        'blacklist_field_ids': [],
        'metadata_field_ref': 'description',
    }
    
    # filter all fields to get all authorized fields            
    def get_authorized_fields(self, cr, uid, model, context=None):
        print 'get authorizeed fields \n'
        output = self.pool[model].fields_get(cr,uid,context=context)
        id_model = self.search(cr,uid,[('model','=',model),], context=context)
        # for elem in blacklist
        for elem in [field.name for field in self.browse(cr,uid,id_model).blacklist_field_ids]:
            output.pop(elem, None)
        for key, val in self.pool[model]._inherits.iteritems():
            output.pop(val,None)
        for key, val in output.iteritems():
            if 'relation' in val and val['relation'] == 'ir.attachment':
                print val['type']
                val['type'] = 'manyBinary2many' if ((val['type'] == 'many2many') or (val['type'] == 'one2many')) else 'oneBinary2many'
                print val['type']

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
    
