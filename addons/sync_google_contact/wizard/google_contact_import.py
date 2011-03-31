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
import datetime
import dateutil
from dateutil.parser import *
from pytz import timezone
import os

try:
    import gdata
    import gdata.contacts.service
    import gdata.contacts
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

from osv import fields,osv
from tools.translate import _
import tools

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
        
        gd_client = google.google_login(user_obj.gmail_user,user_obj.gmail_password,type='group')
        if not gd_client:
            raise osv.except_osv(_('Error'), _("Authentication fail check the user and password !"))
        
        res = []
        query = gdata.contacts.service.GroupsQuery(feed='/m8/feeds/groups/default/full')
        if gd_client:
            groups = gd_client.GetFeed(query.ToUri())
            for grp in groups.entry:
                res.append((grp.id.text, grp.title.text))
        res.append(('all','All Groups'))
        return res

    _columns = {
        'create_partner': fields.selection([('create_all','Create partner for each contact'),('create_address','Import only address')],'Options'),
        'customer': fields.boolean('Customer', help="Check this box to set newly created partner as Customer."),
        'supplier': fields.boolean('Supplier', help="Check this box to set newly created partner as Supplier."),
        'group_name': fields.selection(_get_group, "Group Name", size=32,help="Choose which group to import, By default it takes all."),
     }

    _defaults = {
        'create_partner': 'create_all',
        'group_name': 'all',
    }

    def create_partner(self, cr, uid, data={}, context=None):
        partner_obj = self.pool.get('res.partner')
        partner_id = partner_obj.create(cr, uid, {
                                                  'name': data.get('name',''), 
                                                  'address' : [(6, 0, [data['address_id']])],
                                                  'customer': data.get('customer', False),
                                                  'supplier': data.get('supplier', False)
                                        }, context=context)
        return partner_id

    def import_contact(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids, context=context)[0]

        user_obj = self.pool.get('res.users').browse(cr, uid, uid)

        gmail_user = user_obj.gmail_user
        gmail_pwd = user_obj.gmail_password

        google = self.pool.get('google.login')
        gd_client = google.google_login(gmail_user, gmail_pwd, type='contact')

        if not gd_client:
            raise osv.except_osv(_('Error'), _("Please specify correct user and password !"))

        if obj.group_name not in ['all']:
            query = gdata.contacts.service.ContactsQuery()
            query.group = obj.group_name
            contact = gd_client.GetContactsFeed(query.ToUri())
        else:
            contact = gd_client.GetContactsFeed()

        ids = self.create_contact(cr, uid, ids, gd_client, contact, option=obj.create_partner,context=context)
        if not ids:
            return {'type': 'ir.actions.act_window_close'}

        return {
                'name': _(obj.create_partner =='create_all' and 'Partners') or _('Contacts'),
                'domain': "[('id','in', ["+','.join(map(str,ids))+"])]",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': obj.create_partner =='create_all' and 'res.partner' or 'res.partner.address',
                'context': context,
                'views': [(False, 'tree'),(False, 'form')],
                'type': 'ir.actions.act_window',
        }

    def create_contact(self, cr, uid, ids, gd_client, contact, option,context=None):
        model_obj = self.pool.get('ir.model.data')
        addresss_obj = self.pool.get('res.partner.address')
        addresses = []
        partner_ids = []
        contact_ids = []
        if 'tz' in context and context['tz']:
            time_zone = context['tz']
        else:
            time_zone = tools.get_server_timezone()
        au_tz = timezone(time_zone)
        
        while contact:
            for entry in contact.entry:
                data = self._retreive_data(entry)
                google_id = data.pop('id')
                model_data = {
                    'name':  google_id,
                    'model': 'res.partner.address',
                    'module': 'sync_google_contact',
                    'noupdate': True
                }

                data_ids = model_obj.search(cr, uid, [('model','=','res.partner.address'), ('name','=', google_id)])
                if data_ids:
                    contact_ids = [model_obj.browse(cr, uid, data_ids[0], context=context).res_id]
                elif data['email']:
                    contact_ids = addresss_obj.search(cr, uid, [('email', 'ilike', data['email'])])

                if contact_ids:
                    addresses.append(contact_ids[0])
                    address = addresss_obj.browse(cr, uid, contact_ids[0], context=context)
                    google_updated = entry.updated.text
                    utime = dateutil.parser.parse(google_updated)
                    au_dt = au_tz.normalize(utime.astimezone(au_tz))
                    updated_dt = datetime.datetime(*au_dt.timetuple()[:6]).strftime('%Y-%m-%d %H:%M:%S')
                    if address.write_date < updated_dt:
                        self.update_contact(cr, uid, contact_ids, data, context=context)
                    res_id = contact_ids[0]
                if not contact_ids:
                    #create or link to an existing partner only if it's a new contact
                    res_id = addresss_obj.create(cr, uid, data, context=context)
                    data['address_id'] = res_id
                    if option == 'create_all':
                        obj = self.browse(cr, uid, ids, context=context)[0]
                        data['customer'] = obj.customer
                        data['supplier'] = obj.supplier
                        partner_id = self.create_partner(cr, uid, data, context=context)
                        partner_ids.append(partner_id)
                    addresses.append(res_id)
                        
                if not data_ids: #link to google_id if it was not the case before            
                    model_data.update({'res_id': res_id})
                    model_obj.create(cr, uid, model_data, context=context)

            next = contact.GetNextLink()
            contact = next and gd_client.GetContactsFeed(next.href) or None

        if option == 'create_all':
            return partner_ids
        else:
            return addresses
        
    def _retreive_data(self, entry):
        data = {}
        data['id'] = entry.id.text
        name = tools.ustr(entry.title.text)
        if name == "None":
            name = entry.email[0].address
        data['name'] = name
        emails = ','.join(email.address for email in entry.email)
        data['email'] = emails
        
        if entry.phone_number:
            for phone in entry.phone_number:
                if phone.rel == gdata.contacts.REL_WORK:
                    data['phone'] = phone.text
                if phone.rel == gdata.contacts.PHONE_MOBILE:
                    data['mobile'] = phone.text
                if phone.rel == gdata.contacts.PHONE_WORK_FAX:
                    data['fax'] = phone.text
        return data

    def update_contact(self, cr, uid, contact_ids, data, context=None):
        addresss_obj = self.pool.get('res.partner.address')
        vals = {}
        addr = addresss_obj.browse(cr,uid,contact_ids)[0]
        name = str((addr.name or addr.partner_id and addr.partner_id.name or '').encode('utf-8'))

        if not name:
            vals['name'] = data.get('name','')
        if not addr.email:
            vals['email'] = data.get('email','')
        if not addr.mobile:
            vals['mobile'] = data.get('mobile','')
        if not addr.phone:
            vals['phone'] = data.get('phone','')
        if not addr.fax:
            vals['fax'] = data.get('fax','')
        
        addresss_obj.write(cr, uid, contact_ids, vals, context=context)
        return {'type': 'ir.actions.act_window_close'}

synchronize_google_contact()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
