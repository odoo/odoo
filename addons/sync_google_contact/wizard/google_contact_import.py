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

from osv import fields,osv
from tools.translate import _
import tools
try:
    import gdata
    import gdata.contacts.service
    import gdata.contacts
    import gdata.contacts.client
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

class google_base_import(osv.osv_memory):
    _inherit = 'synchronize.base.contact.wizard.import'

    def _get_tools_name(self, cr, user, context):
        """
        @return the list of value of the selection field
        should be overwritten by subclasses
        """
        names = super(google_base_import, self)._get_tools_name(cr, user, context=context)
        names.append(('gmail','Gmail address book'))
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
        gd_client = google.google_login(cr,uid,user_obj.gmail_user,user_obj.gmail_password,type='group')
        query = gdata.contacts.client.ContactsQuery(feed='/m8/feeds/groups/default/full')
        res = []
        if gd_client:
            groups = gd_client.GetGroups(q=query)
            for grp in groups.entry:
                res.append((grp.id.text, grp.title.text))
        res.append(('none','None'))
        res.append(('all','All Groups'))
        return res

    _columns = {
        'create_partner': fields.boolean('Create Partner', help="It will create Partner for given gmail user otherwise only adds contacts in Partner Addresses.")  ,
        'group_name': fields.selection(_get_group, "Group Name", size=32,help="Choose which group to import, By defult it take all "),
     }

    _defaults = {
        'create_partner': True,
        'group_name': 'all',
    }

    def create_partner(self, cr, uid, data={}, context=None):
        partner_obj = self.pool.get('res.partner')
        name = data.get('name','')
        partner_id = partner_obj.search(cr, uid, [('name','ilike',name)], context=context)
        if not partner_id:
            partner_id.append(partner_obj.create(cr, uid, {'name': name, 'address' : [(6, 0, [data['address_id']])]}, context=context))
        return partner_id, data

    def import_contact(self, cr, uid, ids, context=None):
        obj=self.browse(cr, uid, ids, context=context)[0]
        if obj.group_name == 'none':
            return { 'type': 'ir.actions.act_window_close' }

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)

        gmail_user = user_obj.gmail_user
        gamil_pwd = user_obj.gmail_password

        google = self.pool.get('google.login')
        gd_client = google.google_login(cr,uid,user_obj.gmail_user,user_obj.gmail_password,type='contact')

        if not gmail_user or not gamil_pwd:
            raise osv.except_osv(_('Error'), _("Please specify the user and password !"))

        if obj.group_name not in ['all','none']:
            query = gdata.contacts.service.ContactsQuery()
            query.group =obj.group_name
            contact = gd_client.GetContactsFeed(query.ToUri())
        else:
            contact = gd_client.GetContactsFeed()

        ids = self.create_contact( cr, uid, gd_client,contact, partner_id=obj.create_partner,context=context)
        if not ids:
            return {'type': 'ir.actions.act_window_close'}

        return {
                'name': _('Partner'),
                'domain': "[('id','in', ["+','.join(map(str,ids))+"])]",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': obj.create_partner and 'res.partner' or 'res.partner.address',
                'context': context,
                'views': [(False, 'tree'),(False, 'form')],
                'type': 'ir.actions.act_window',
        }


    def create_contact(self, cr, uid, gd_client,contact, partner_id=False,context=None):
        model_obj = self.pool.get('ir.model.data')
        addresss_obj = self.pool.get('res.partner.address')
        addresses = []
        partner_ids = []
        contact_ids=[]
        while contact:
            for entry in contact.entry:
                data = {}
                model_data = {
                    'name': 'google_contacts_information_%s' %(entry.id.text),
                    'model': 'res.partner.address',
                    'module': 'sync_google_contact',
                }
                name = tools.ustr(entry.title.text)
                if name == "None":
                    name = entry.email[0].address

                google_id = entry.id.text
                emails = ','.join(email.address for email in entry.email)
                if name and name != 'None':
                    data['name'] = name

                if google_id:
                    model_data.update({'google_id': google_id})
                if entry.phone_number:
                    for phone in entry.phone_number:
                        if phone.rel == gdata.contacts.REL_WORK:
                            data['phone'] = phone.text
                        if phone.rel == gdata.contacts.PHONE_MOBILE:
                            data['mobile'] = phone.text
                        if phone.rel == gdata.contacts.PHONE_WORK_FAX:
                            data['fax'] = phone.text

                data_ids = model_obj.search(cr, uid, [('google_id','=',google_id)])
                if data_ids:
                    contact_ids = [model_obj.browse(cr, uid, data_ids[0], context=context).res_id]
                elif emails:
                    data['email'] = emails
                    contact_ids = addresss_obj.search(cr, uid, [('email','ilike',emails)])

                if contact_ids:
                    addresses.append(contact_ids[0])
                    self.update_contact(cr, uid, contact_ids, data, context=context)
                    data_ids = model_obj.search(cr, uid, [('res_id','=',contact_ids[0]), ('google_id','=','')])
                    model_data.update({'google_id': google_id})
                    model_obj.write(cr, uid, data_ids, model_data, context=context)
                if not contact_ids:
                    #create or link to an existing partner only if it's a new contact
                    res_id = addresss_obj.create(cr, uid, data, context=context)
                    data['address_id'] = res_id
                    if partner_id:
                        partner_id, data = self.create_partner(cr, uid, data, context=context)
                        partner_ids.append(partner_id[0])
                    addresses.append(res_id)
                    model_data.update({'res_id': res_id})
                    model_obj.create(cr, uid, model_data, context=context)

            next = contact.GetNextLink()
            contact = next and gd_client.GetContactsFeed(next.href) or None

        if partner_id:
            return partner_ids
        else:
            return addresses

    def update_contact(self, cr, uid, contact_ids, data,context=None):
        addresss_obj = self.pool.get('res.partner.address')
        if context==None:
            context={}
        res = {}
        addr = addresss_obj.browse(cr,uid,contact_ids)[0]
        name = str((addr.name or addr.partner_id and addr.partner_id.name or '').encode('utf-8'))
        addres=addr.partner_id
        email = addr.email
        phone = addr.phone
        mobile = addr.mobile
        fax = addr.fax
        if not name:
            res['name']=data.get('name','')
        if not email:
            res['email']=data.get('email','')
        if not mobile:
            res['mobile']=data.get('mobile','')
        if not phone:
            res['phone']=data.get('phone','')
        if not fax:
            res['fax']=data.get('fax','')
        if data.get('partner_id') and not addres :
            res['partner_id'] = data.get('partner_id')
        addresss_obj.write(cr,uid,contact_ids,res,context=context)
        return {}

synchronize_google_contact()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
