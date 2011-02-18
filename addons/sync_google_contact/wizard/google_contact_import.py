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

class google_contact_import(osv.osv_memory):
    _inherit = 'google.login'
    
    def default_get(self, cr, uid, fields, context=None):
        res = super(google_contact_import, self).default_get(cr, uid, fields, context=context)
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        if 'user' in fields:
            res.update({'user': user_obj.gmail_user})
        if 'password' in fields:
            res.update({'password': user_obj.gmail_password})
        return res
    
    def check_login_contact(self, cr, uid, ids, context=None):
        gd_client = self.check_login(cr, uid, ids, context=context)
        if not gd_client:
           raise osv.except_osv(_('Error'), _("Authication fail check  the user and password !"))    
        data_obj = self.pool.get('ir.model.data')
        data_id = data_obj._get_id(cr, uid, 'sync_google_contact', 'view_synchronize_google_contact_import_form')
        view_id = False
        if data_id:
            view_id = data_obj.browse(cr, uid, data_id, context=context).res_id        
        value = {
            'name': _('Import Contact'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'synchronize.base',
            'view_id': False,
            'context': context,
            'views': [(view_id, 'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        return value        
         
google_contact_import()

class synchronize_google_contact(osv.osv_memory):
    _name = "synchronize.base"    
    _inherit = 'synchronize.base'
    
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
        'tools': fields.selection([('gmail','Gmail')], 'Tools'),
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
            if obj.tools == 'gmail':
                while contact:
                    for entry in contact.entry:
                        partner_id = False
                        name = tools.ustr(entry.title.text)
                        phone_numbers = ','.join(phone_number.text for phone_number in entry.phone_number)
                        emails = ','.join(email.address for email in entry.email)
                        data = {
                                'name': name or '',
                                'phone': phone_numbers,
                                'email': emails,
                        }
                        if obj.create_partner and obj.group_name == 'all':
                            if name:
                                partner_id, data = self.create_partner(cr, uid, ids, data, context=context)
                                partner_ids.append(partner_id[0])
                            addresses.append(addresss_obj.create(cr, uid, data, context=context))
                        contact_ids = addresss_obj.search(cr, uid, [('email','ilike',emails)])
                        if not contact_ids:
                            if obj.group_name and entry.group_membership_info:
                                for grp in entry.group_membership_info:
                                    if grp.href == obj.group_name:
                                        if obj.create_partner:
                                            partner_id, data = self.create_partner(cr, uid, ids, data, context=context)
                                            partner_ids.append(partner_id[0])
                                        addresses.append(addresss_obj.create(cr, uid, data, context=context))                        
                            else:
                                if obj.group_name == 'all':
                                    addresses.append(addresss_obj.create(cr, uid, data, context=context))
                        else:
                            addresss_obj.write(cr, uid, contact_ids, data, context=context)
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
