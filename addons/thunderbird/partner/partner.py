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

from osv import osv
import base64
import email
import tools

class thunderbird_partner(osv.osv_memory):
    _name = "thunderbird.partner"
    _description="Thunderbid Plugin Tools"

    def create_contact(self,cr,user,vals):
        dictcreate = dict(vals)
        # Set False value if 'undefined' for record. Id User does not spicify the values, Thunerbird set 'undefined' by default for new contact.
        for key in dictcreate:
            if dictcreate[key] == 'undefined':
                dictcreate[key] = False
        if not eval(dictcreate.get('partner_id')):
            dictcreate.update({'partner_id': False})
        create_id = self.pool.get('res.partner.address').create(cr, user, dictcreate)
        return create_id

    def history_message(self, cr, uid, vals):
        dictcreate = dict(vals)
        ref_ids = str(dictcreate.get('ref_ids')).split(';')
        msg = dictcreate.get('message')
        mail = msg
        msg = self.pool.get('email.message').parse_message(msg)
        subject = msg.get('Subject', False)
        thread_pool = self.pool.get('email.thread')
        message_id = msg.get('message-id', False)
        msg_pool = self.pool.get('email.message')
        msg_ids = []
        res = {}
        res_ids = []
        obj_list= ['crm.lead','project.issue','hr.applicant','res.partner']
        for ref_id in ref_ids:
            ref = ref_id.split(',')
            model = ref[0]
            res_id = int(ref[1])
            if message_id:
                msg_ids = msg_pool.search(cr, uid, [('message_id','=',message_id),('res_id','=',res_id),('model','=',model)])
                if msg_ids and len(msg_ids):
                    continue
            if model not in obj_list:
                res={}
                obj_attch = self.pool.get('ir.attachment')
                ls = ['*', '/', '\\', '<', '>', ':', '?', '"', '|', '\t', '\n',':','~']
                sub = msg.get('subject','NO-SUBJECT').replace(' ','')
                if sub.strip() == '':
                   sub = 'NO SBUJECT'
                fn = sub
                for c in ls:
                   fn = fn.replace(c,'')
                if len(fn) > 64:
                   l = 64 - len(fn)
                   f = fn.split('-')
                   fn = '-'.join(f[1:])
                   if len(fn) > 64:
                      l = 64 - len(fn)
                      f = fn.split('.')
                      fn = f[0][0:l] + '.' + f[-1]
                fn = fn[:-4]+'.eml'
                res['res_model'] = model
                res['name'] = msg.get('subject','NO-SUBJECT')+".eml"
                res['datas_fname'] = fn
                res['datas'] = base64.b64encode(mail)
                res['res_id'] = res_id
                obj_attch.create(cr, uid, res)
            threads = self.pool.get(model).browse(cr, uid, res_id)
            thread_pool.history(cr, uid, [threads], _('receive'), history=True,
                            subject = msg.get('subject'),
                            email = msg.get('to'),
                            details = msg.get('body'),
                            email_from = msg.get('from'),
                            email_cc = msg.get('cc'),
                            message_id = msg.get('message-id'),
                            references = msg.get('references', False) or msg.get('in-reply-to', False),
                            attach = msg.get('attachments', {}),
                            email_date = msg.get('date'))
            res_ids.append(res_id)
        return len(res_ids)

    def process_email(self, cr, uid, vals):
        dictcreate = dict(vals)
        model = str(dictcreate.get('model'))
        message = dictcreate.get('message')
        return self.pool.get('email.thread').process_email(cr, uid, model, message, attach=True, context=None)

    def search_message(self, cr, uid, message, context=None):
        #@param message: string of mail which is read from EML File
        #@return model,res_id
        references = []
        dictcreate = dict(message)
        msg = dictcreate.get('message')
        msg = self.pool.get('email.message').parse_message(msg)
        message_id = msg.get('message-id')
        refs =  msg.get('references',False)
        references = False
        if refs:
            references = refs.split()
        msg_pool = self.pool.get('email.message')
        model = ''
        res_id = 0
        if message_id:
            msg_ids = msg_pool.search(cr, uid, [('message_id','=',message_id)])
            if msg_ids and len(msg_ids):
                msg = msg_pool.browse(cr, uid, msg_ids[0])
                model = msg.model
                res_id = msg.res_id
            else:
                if references :
                    msg_ids = msg_pool.search(cr, uid, [('message_id','in',references)])
                    if msg_ids and len(msg_ids):
                        msg = msg_pool.browse(cr, uid, msg_ids[0])
                        model = msg.model
                        res_id = msg.res_id
        return (model,res_id)


    def search_contact(self, cr, user, email):
        address_pool = self.pool.get('res.partner.address')
        address_ids = address_pool.search(cr, user, [('email','=',email)])
        res = {}

        if not address_ids:
            res = {
                'email': '',
            }
        else:
            address_id = address_ids[0]
            address = address_pool.browse(cr, user, address_id)
            res = {
                'partner_name': address.partner_id and address.partner_id.name or '',
                'contactname': address.name,
                'street': address.street or '',
                'street2': address.street2 or '',
                'zip': address.zip or '',
                'city': address.city or '',
                'country': address.country_id and address.country_id.name or '',
                'state': address.state_id and address.state_id.name or '',
                'email': address.email or '',
                'phone': address.phone or '',
                'mobile': address.mobile or '',
                'fax': address.fax or '',
                'partner_id': address.partner_id and str(address.partner_id.id) or '',
                'res_id': str(address.id),
            }
        return res.items()

    def update_contact(self, cr, user, vals):
        dictcreate = dict(vals)
        res_id = dictcreate.get('res_id',False)
        result = {}
        address_pool = self.pool.get('res.partner.address')
        if not (dictcreate.get('partner_id')): # TOCHECK: It should be check res_id or not
            dictcreate.update({'partner_id': False})
            create_id = address_pool.create(cr, user, dictcreate)
            return create_id

        if res_id:
            address_data = address_pool.read(cr, user, int(res_id), [])
            result = {
               'partner_id': address_data['partner_id'] and address_data['partner_id'][0] or False, #TOFIX: parter_id should take from address_data
               'country_id': dictcreate['country_id'] and int(dictcreate['country_id'][0]) or False,
               'state_id': dictcreate['state_id'] and int(dictcreate['state_id'][0]) or False,
               'name': dictcreate['name'],
               'street': dictcreate['street'],
               'street2': dictcreate['street2'],
               'zip': dictcreate['zip'],
               'city': dictcreate['city'],
               'phone': dictcreate['phone'],
               'fax': dictcreate['fax'],
               'mobile': dictcreate['mobile'],
               'email': dictcreate['email'],
            }
        address_pool.write(cr, user, int(res_id), result )
        return True

    def create_partner(self,cr,user,vals):
        dictcreate = dict(vals)
        partner_obj = self.pool.get('res.partner')
        search_id =  partner_obj.search(cr, user,[('name','=',dictcreate['name'])])
        if search_id:
            return 0
        create_id =  partner_obj.create(cr, user, dictcreate)
        return create_id

    def search_document(self,cr,user,vals):
        dictcreate = dict(vals)
        search_id = self.pool.get('ir.model').search(cr, user,[('model','=',dictcreate['model'])])
        return (search_id and search_id[0]) or 0

    def search_checkbox(self,cr,user,vals):
        if vals[0]:
            value = vals[0][0]
        if vals[1]:
            obj = vals[1];
        name_get=[]
        er_val=[]
        for object in obj:
            dyn_object = self.pool.get(object)
            if object == 'res.partner.address':
                search_id1 = dyn_object.search(cr,user,[('name','ilike',value)])
                search_id2 = dyn_object.search(cr,user,[('email','=',value)])
                if search_id1:
                    name_get.append(object)
                    name_get.append(dyn_object.name_get(cr, user, search_id1))
                elif search_id2:
                    name_get.append(object)
                    name_get.append(dyn_object.name_get(cr, user, search_id2))
            else:
                try:
                    search_id1 = dyn_object.search(cr,user,[('name','ilike',value)])
                    if search_id1:
                        name_get.append(object)
                        name_get.append(dyn_object.name_get(cr, user, search_id1))
                except:
                    er_val.append(object)
                    continue
        if len(er_val) > 0:
            name_get.append('error')
            name_get.append(er_val)
        return name_get
    def list_alldocument(self,cr,user,vals):
        obj_list= [('crm.lead','CRM Lead'),('project.issue','Project Issue'), ('hr.applicant','HR Applicant')]
        object=[]
        model_obj = self.pool.get('ir.model')
        for obj in obj_list:
            if model_obj.search(cr, user, [('model', '=', obj[0])]):
                object.append(obj)
        return object

    def list_allcountry(self,cr,user,vals):
        country_list = []
        cr.execute("SELECT id, name from res_country order by name")
        country_list = cr.fetchall()
        return country_list


    def list_allstate(self,cr,user,vals):
         cr.execute("select id, name  from res_country_state  where country_id = %s order by name",(vals,) )
         state_country_list = cr.fetchall()
         return state_country_list


    def search_document_attachment(self,cr,user,vals):
        model_obj = self.pool.get('ir.model')
        object=''
        for obj in vals[0][1].split(','):
            if model_obj.search(cr, user, [('model', '=', obj)]):
                object += obj + ","
            else:
                object += "null,"
        return object

thunderbird_partner()
