# -*- coding: utf-8 -*-
import base64

import json

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.tools.translate import _
import pudb

class form_builder(http.Controller):
    #Load custom template as success page and build it with the inserted record
    @http.route('/website_form/thanks/<path:template>', type='http', auth="public", website=True)
    def thanks_page(self, template):
        try:
            request.website.get_template(template)
        except ValueError:
            return request.redirect('/'+template)

        model = request.session.get('form_builder_model')
        record = request.env.sudo()[model].browse(request.session.get('form_builder_id'))
        if not record.exists():
            return False
        return request.website.render(template, {"record":record})

    #check and insert values from the form on the model <model>
    @http.route('/website_form/<model>', type='http', auth="public", methods=['POST'], website=True)
    def website_form(self, model, **kwargs):

        model_record = request.env['ir.model'].search([('model', '=', model)])

        if not model_record.website_form_access:
            return None

        data = self.extract_data(model_record, ** kwargs)

        try:     
            if(any(data['error'])):
                success = 0
            else:
                id_list   = self.insert_attachment(model_record, data)
                id_record = self.insert_record(model_record, data)
                self.insert_message(model_record, data, id_record)

                request.env['ir.attachment'].browse(id_list).sudo().write({'res_id': id_record})

                request.session['form_builder_model'] = model
                request.session['form_builder_id']    = id_record
                success = id_record
        except ValueError:
            success = 0

        if request.httprequest.is_xhr:
            if data['error']:
                return json.dumps({'id': success, 'fail_required' : data['error']})
            return json.dumps({'id': success, 'fail_required': None})
        else:
            if data['error']:
                return self.thanks_page('default.fail.'+model)
            return self.thanks_page('default.thanks.'+model)


    # Constants string to make custom info and metadata readable on a text field

    _custom_label    = "%s\n________________________________________________\n\n" % _("Custom infos")   # Extra data from custom fields
    _meta_label      = "%s\n________________________________________________\n\n" % _("Metadata")       # meta data

    # Dict of dynamically called filters following type of field to be fault tolerent

    def get_int(self,x):
        return int(''.join(ele for ele in x if ele.isdigit()) or 0)

    def get_float(self,x):
        return float(''.join(ele for ele in x if ele.isdigit() or ele == '.') or 0.0)

    def char(self, label, input):
        return input
    
    def text(self, label, input):
        return input

    def html(self, label, input):
        return input
    
    def many2one(self, label, input):
        return int(self.get_int(input))
    
    def one2many(self, label, input):
        output = []
        input = input.split(',')
        for elem in input:
            input_int = int(self.get_int(elem))
            if input_int :
                output.append(input_int)
        return output
    
    def many2many(self, label, input, *args):
        op = (6,0)
        if len(args) == 1:
            op = args[0]
        output = self.one2many(label,input)
        return [op + (output,)]
    
    def selection(self, label, input):
        return int(self.get_int(input))
    
    def boolean(self, label, input):
        return (input != 0)
    
    def integer(self, label, input):
        return int(self.get_int(input))
    
    def float(self, label, input):
        return float(self.get_float(input))

    _filter = {'char': char, 'text': text, 'html': html, 'many2one': many2one,
               'one2many': one2many, 'many2many':many2many, 'selection': selection,
               'boolean': boolean,'integer': integer,'float': float}



    # Extract all data sent by the form and sort its on several properties
    def extract_data(self, model, **kwargs):

        data = {
            'files'     : [],                    # List of attached files
            'post'      : {},                    # Dict of values to create entry on the model
            'custom'    : '',
            'meta'      : '',
            'error'     : '',
            'message'   : { 
                            'body'           : _('<p>Attatched files : </p>'),
                            'model'          : model.model,
                            'type'           : 'comment',
                            'no_auto_thread' : False,
                            'attachment_ids' : [],
                }
        }
        #authorized_fields = [field.name for field in model.get_authorized_fields()]
        i = 0
        full_authorized_fields = model.get_authorized_fields();
        authorized_fields = [key for key, val in full_authorized_fields.iteritems()]

        for field_name, field_value in kwargs.items():
            if hasattr(field_value, 'filename'):
                field_value.field_name = field_name
                data['files'].append(field_value)

            elif field_name in authorized_fields:
                field_filtered = self._filter[full_authorized_fields[field_name]['type']](self, field_name, field_value)
                if field_filtered: data['post'][field_name] = field_filtered
                
            elif field_name != 'context':
                data['custom'] += "%s : %s\n" % (field_name, field_value)
                
        environ = request.httprequest.headers.environ
        
        if(request.website.website_form_enable_metadata):
            data['meta'] += "%s : %s\n%s : %s\n%s : %s\n%s : %s\n" % ("IP"                , environ.get("REMOTE_ADDR"), 
                                                                      "USER_AGENT"        , environ.get("HTTP_USER_AGENT"),
                                                                      "ACCEPT_LANGUAGE"   , environ.get("HTTP_ACCEPT_LANGUAGE"),
                                                                      "REFERER"           , environ.get("HTTP_REFERER"))
        dest_model = request.env[model.model]
        if hasattr(dest_model, "website_form_input_filter"):
            data = dest_model.website_form_input_filter(data)

        data['error'] = list(set(label for label, field in full_authorized_fields.iteritems() if not data['post'].get(label) and field['required']))
        return data
    
    def insert_message(self, model, data, id_record):
        if model.name == 'mail.mail':
            return True
        if not data['message']['attachment_ids']:
            return True
        data['message']['res_id'] = id_record
        return request.env['mail.message'].sudo().create(data['message']).id

    def insert_record(self, model, data):
        values = data['post']
        if model.website_form_default_field_id.name not in values:
            values[model.website_form_default_field_id.name] = ''
        values[model.website_form_default_field_id.name] += "\n\n" + (self._custom_label if (data['custom'] != '') else '') + data['custom'] + \
                                                            "\n\n" + (self._meta_label   if (data['meta']   != '') else '') + data['meta']

        return request.env[model.model].sudo().create(values).id

    # Link all files attached on the form
    def insert_attachment(self, model, data):
        id_list = []
        auth_files = map(lambda x: x, model.get_authorized_fields())
        for file in data['files']:
            file.field_name = file.field_name.split('[')[0]
            attachment_value = {
                'name': file.filename,
                'res_name': file.filename,
                'datas': base64.encodestring(file.read()),
                'datas_fname': file.filename,
            }
            id_file = request.env['ir.attachment'].sudo().create(attachment_value)
            id_list.append(id_file.id)
            if file.field_name in auth_files:
                if file.field_name not in data['post'].keys(): 
                    data['post'][file.field_name] = []
                data['post'][file.field_name].append((4,id_file.id))

            else:
                data['message']['attachment_ids'].append((4,id_file.id))
        return id_list
