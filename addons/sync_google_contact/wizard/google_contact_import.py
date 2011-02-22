# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 L (<http://tiny.be>).
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

from osv import fields,osv
from tools.translate import _
import tools
import gdata.contacts

class google_base_import(osv.osv_memory):
    _inherit = 'synchronize.base.contact.wizard.import'

    def _get_tools_name(self, cr, user, context):
        """
        @return the list of value of the selection field
        should be overwritten by subclasses
        """
        names = super(google_base_import, self)._get_tools_name(cr, user, context=context)
        names.append(('gmail','Gmail adress book'))
        return names


    _columns = {
        'tools':  fields.selection(_get_tools_name, 'App to synchronize with'),
    }


    def _get_actions_dic(self, cr, uid, context=None):
        """
            this method should be overwritten in specialize module
            @return the dictonnaries of action
        """
        actions = super(google_base_import, self)._get_actions_dic(cr, uid, context=context)

        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'google_base_account', 'view_google_login_form')
        view_id = False
        if data_id:
            view_id = data_obj.browse(cr, uid, data_id, context=context).res_id

        value = {
            'name': _('Import Contact'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'google.login.contact',
            'view_id': False,
            'context': context,
            'views': [(view_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        actions['gmail'] = value
        return actions

google_base_import()

class google_contact_import(osv.osv_memory):
    _inherit = 'google.login'
    _name = 'google.login.contact'

    def _get_next_action(self, cr, uid, context=None):
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'sync_google_contact', 'view_synchronize_google_contact_import_form')
        view_id = False
        if data_id:
            view_id = data_obj.browse(cr, uid, data_id, context=context).res_id
        value = {
            'name': _('Import Contact'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'synchronize.google.contact.import',
            'view_id': False,
            'context': context,
            'views': [(view_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return value

google_contact_import()

class synchronize_google_contact(osv.osv_memory):
    _name = 'synchronize.google.contact.import'

    def _get_group(self, cr, uid, context=None):
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        google=self.pool.get('google.login')
        gd_client = google.google_login(cr,uid,user_obj.gmail_user,user_obj.gmail_password)
        res = []
        if gd_client:
            groups = gd_client.GetGroupsFeed()
            for grp in groups.entry:
                res.append((grp.id.text, grp.title.text))
        res.append(('none','None'))
        res.append(('all','All Groups'))
        return res

    def _get_default_group(self, cr, uid, context=None):
        return 'all'

    _columns = {
        'create_partner': fields.boolean('Create Partner', help="It will create Partner for given gmail user otherwise only adds contacts in Partner Addresses.")  ,
        'group_name': fields.selection(_get_group, "Group Name", size=32,help="Choose which group to import, By defult it take all "),
     }

    _defaults = {
        'group_name': _get_default_group,
    }

    def create_partner(self, cr, uid, ids, data={}, context=None):
        partner_obj = self.pool.get('res.partner')
        name = data.get('name', '')
        partner_id = partner_obj.search(cr, uid, [('name','ilike',name)], context=context)
        if not partner_id:
            partner_id.append(partner_obj.create(cr, uid, {'name': name}, context=context))
        data.update({'partner_id': partner_id and partner_id[0]})
        return partner_id, data

    def import_contact(self, cr, uid, ids, context=None):
        addresss_obj = self.pool.get('res.partner.address')
        partner_obj = self.pool.get('res.partner')

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)

        gmail_user = user_obj.gmail_user
        gamil_pwd = user_obj.gmail_password

        google = self.pool.get('google.login')
        gd_client = google.google_login(cr,uid,user_obj.gmail_user,user_obj.gmail_password)

        if not gmail_user or not gamil_pwd:
            raise osv.except_osv(_('Error'), _("Please specify the user and password !"))

        contact = gd_client.GetContactsFeed()
        partner_id = []
        addresses = []
        partner_ids = []

        for obj in self.browse(cr, uid, ids, context=context):
            while contact:
                for entry in contact.entry:
                    data={}
                    partner_id = False
                    name = tools.ustr(entry.title.text)
                    google_id = entry.id.text
                    phone_numbers = ','.join(phone_number.text for phone_number in entry.phone_number)
                    if name:
                        data['name'] = name
                    if google_id:
                        data['google_id'] =google_id
                    if entry.phone_number:
                        for phone in entry.phone_number:
                            if phone.rel == gdata.contacts.REL_WORK:
                                data['phone'] = phone.text
                            if phone.rel == gdata.contacts.PHONE_MOBILE:
                                data['mobile'] = phone.text
                            if phone.rel == gdata.contacts.PHONE_WORK_FAX:
                                data['fax'] = phone.text
                    emails = ','.join(email.address for email in entry.email)
                    if emails:
                        data['email'] = emails                    
                        contact_ids = addresss_obj.search(cr, uid, [('email','ilike',emails)])     
                    else:
                        contact_ids = addresss_obj.search(cr, uid, [('google_id','=',google_id)])                             
                    if  contact_ids :
                        res={}
                        addr=addresss_obj.browse(cr,uid,contact_ids)[0]
                        name = str((addr.name or addr.partner_id and addr.partner_id.name or '').encode('utf-8')) 
                        notes = addr.partner_id and addr.partner_id.comment or ''
                        email = addr.email or ''
                        phone = addr.phone or ''
                        mobile = addr.mobile or ''
                        fax = addr.fax or ''
                        if not name or name=='None':
                            res['name']=data.get('name','')
                        if not email:  
                            res['email']=data.get('email','')
                        if not mobile:  
                            res['mobile']=data.get('mobile','')                          
                        if not phone:  
                            res['phone']=data.get('phone','')
                        if not fax:  
                            res['fax']=data.get('fax','')                            
                        addresss_obj.write(cr,uid,contact_ids,res,context=context)
                    else:     
                        if obj.create_partner and obj.group_name == 'all':
                            if name:
                                partner_id, data = self.create_partner(cr, uid, ids, data, context=context)
                                partner_ids.append(partner_id[0])
                            addresses.append(addresss_obj.create(cr, uid, data, context=context))
                        if obj.group_name and entry.group_membership_info and not contact_ids:
                            for grp in entry.group_membership_info:
                                if grp.href == obj.group_name:
                                    if obj.create_partner:
                                        partner_id, data = self.create_partner(cr, uid, ids, data, context=context)
                                        partner_ids.append(partner_id[0])
                                        addresses.append(addresss_obj.create(cr, uid, data, context=context))
                        else:
                                if obj.group_name == 'all' and not contact_ids:
                                    addresses.append(addresss_obj.create(cr, uid, data, context=context))

                if not contact:
                    break
                next = contact.GetNextLink()
                contact = None
                if next:
                    contact = gd_client.GetContactsFeed(next.href)

        if partner_ids:
            return {
                    'name': _('Partner'),
                    'domain': "[('id','in', ["+','.join(map(str,partner_ids))+"])]",
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'res.partner',
                    'context': context,
                    'views': [(False, 'tree'),(False, 'form')],
                    'type': 'ir.actions.act_window',
            }
        elif addresses:
            return {
                    'name': _('Contacts'),
                    'domain': "[('id','in', ["+','.join(map(str,addresses))+"])]",
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'res.partner.address',
                    'context': context,
                    'views': [(False, 'tree'),(False, 'form')],
                    'type': 'ir.actions.act_window',
            }
        else:
            return {'type': 'ir.actions.act_window_close'}

synchronize_google_contact()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
