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

import time
import ir
from osv import osv,fields
import base64
import netsvc
from tools.translate import _

class thunderbird_partner(osv.osv_memory):
    _name = "thunderbird.partner"
    _description="Thunderbid mails"
    _rec_name="sender"

    def mailcreate(self,cr,user,vals):
        dictcreate = dict(vals)
        import email
        header_name = email.Header.decode_header(dictcreate['name'])
        dictcreate['name'] = header_name and header_name[0] and header_name[0][0]
        address_obj = self.pool.get('res.partner.address')
        case_pool = self.pool.get(dictcreate.get('object','crm.lead'))
        partner_ids = address_obj.search(cr,user,[('email','=',dictcreate['email_from'])])
        partner = address_obj.read(cr,user,partner_ids,['partner_id','name'])
        if partner and partner[0] and partner[0]['partner_id']:
            dictcreate.update({'partner_id':partner[0]['partner_id'][0],'partner_name':partner[0]['name']})
        create_id = case_pool.create(cr, user, dictcreate)
        cases = case_pool.browse(cr,user,[create_id])
        case_pool._history(cr, user, cases, _('Archive'), history=True, email=False)
        return create_id

    def create_contact(self,cr,user,vals):
        dictcreate = dict(vals)
        if not eval(dictcreate.get('partner_id')):
            dictcreate.update({'partner_id': False})
        create_id = self.pool.get('res.partner.address').create(cr, user, dictcreate)
        return create_id

    def search_contact(self, cr, user, vals):
        address_obj = self.pool.get('res.partner.address')
        partner = address_obj.search(cr, user,[('email','=',vals)])
        res = {}
        res1 = {}
        if not partner:
            res1 = {
                'email': '',
                    }
            return res1.items()

        if partner:
            partner=partner[0]
            data = address_obj.read(cr,user, partner)
            res = {
                'partner_name': data['partner_id'] and data['partner_id'][1] or '',
                'contactname': data['name'] or '',
                'street': data['street'] or '',
                'street2': data['street2'] or '',
                'zip': data['zip'] or '',
                'city': data['city'] or '',
                'country': data['country_id'] and data['country_id'][1] or '',
                'state': data['state_id'] and data['state_id'][1] or '',
                'email': data['email'] or '',
                'phone': data['phone'] or '',
                'mobile': data['mobile'] or '',
                'fax': data['fax'] or '',
                'res_id': str(partner),
            }
        return res.items()

    def update_contact(self,cr,user,vals):
        dictcreate = dict(vals)
        res_id = dictcreate.get('res_id',False)
        result={}
        if res_id:
            address_obj = self.pool.get('res.partner.address')
            address_data = address_obj.read(cr, user, int(res_id), [])
            result={           'partner_id': address_data['partner_id'] and address_data['partner_id'][0] or False,
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
        address_obj.write(cr, user,int(res_id),result )
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

    def create_attachment(self,cr,user,vals):
        dictcreate = dict(vals)
        datas = [dictcreate['datas']]
        name = [dictcreate['name']]
        f_name = [dictcreate['datas_fname']]
        if(dictcreate['datas'].__contains__(',')):
            name = dictcreate['name'].split(',')
            datas = dictcreate['datas'].split(',')
            f_name = dictcreate['datas_fname'].split(',')
        for i in range(0,datas.__len__()):
            dictcreate['name'] = name[i]
            dictcreate['datas'] = datas[i]
            dictcreate['datas_fname'] = f_name[i]
            create_id = self.pool.get('ir.attachment').create(cr,user,dictcreate)
        return 0

    def list_alldocument(self,cr,user,vals):
        obj_list= [('crm.lead','Lead'),('project.issue','Project Issue'), ('hr.applicant','HR Recruitment')]
        object=[]
        model_obj = self.pool.get('ir.model')
        for obj in obj_list:
            if model_obj.search(cr, user, [('model', '=', obj[0])]):
                object.append(obj)
        return object

    def list_allcountry(self,cr,user,vals):
        country_list = []
        cr.execute("SELECT id, name from res_country")
        country_list = cr.fetchall()
        return country_list

    def list_allstate(self,cr,user,vals):
        cr.execute("SELECT id, name from res_country_state")
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
