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

from sync_google_contact import sync_google_contact

class google_contact_import(osv.osv_memory):
    _name = "synchronize.base"    
    _inherit = 'synchronize.base'
    _columns = {
        'tools': fields.selection([('gmail','Gmail')], 'Tools'),
        'create_partner': fields.selection([('group','Group'),('gmail_user','Gmail user')], 'Create Partner'),
     }
        
    def import_contact(self, cr, uid, ids, context=None):
        # Only see the result, we will change the code
        
        addresss_obj = self.pool.get('res.partner.address')
        partner_obj = self.pool.get('res.partner')
        user_obj = self.pool.get('res.users').browse(cr, uid, uid)
        gmail_user = user_obj.gmail_user
        gamil_pwd = user_obj.gmail_password
        if not gmail_user or not gamil_pwd:
            raise osv.except_osv(_('Error'), _("Please specify the user and password !"))      

        google_obj = sync_google_contact.google_lib(gmail_user, gamil_pwd)
        contact = google_obj._get_contact()      
        partner_id = []
        partner_name = []
        group_links = {}

        for obj in self.browse(cr, uid, ids, context=context):
            if obj.create_partner == 'group':
                groups = google_obj._get_contact_allGroups()
                for grp in groups.entry:
                    partner_name.append(grp.title.text)
                    group_links[grp.title.text] = grp.id.text
            elif obj.create_partner == 'gmail_user':
                google_obj = sync_google_contact.google_lib(gmail_user, gamil_pwd)
                contact = google_obj._get_contact()
                for user in contact.author:
                    partner_name.append(user.name.text)
                
            # Creating partner for selected option.
            for name in partner_name:
                partner_id = partner_obj.search(cr, uid, [('name','ilike',name)], context=context)
                if not partner_id:
                    partner_id.append(partner_obj.create(cr, uid, {'name': name}, context=context))
                contact = google_obj._get_contact()
                contact_ids = []
                link = group_links.get(name)
                while contact:
                    for entry in contact.entry:
                        google_id = entry.id.text
                        contact_name = entry.title.text
                        phone_numbers = ','.join(phone_number.text for phone_number in entry.phone_number)
                        emails = ','.join(email.address for email in entry.email)
                        data = {
                                'name': contact_name,
                                'phone': phone_numbers,
                                'email': emails,
                                'google_id': google_id,
                                'partner_id': partner_id and partner_id[0]
                         }
                        if entry.group_membership_info and link:
                            for grp in entry.group_membership_info:
                                if grp.href == link:
                                    addresss_obj.create(cr, uid, data, context=context)
                        else:
                            if obj.create_partner == 'gmail_user':
                                data.update({'partner_id': partner_id and partner_id[0]})
                            else:
                                data.update({'partner_id': False})
                                continue
                            contact_ids = addresss_obj.search(cr, uid, [('email','ilike',emails)])
                            if not contact_ids:
                                addresss_obj.create(cr, uid, data, context=context)
                    if not contact:
                        break
                    next = contact.GetNextLink()
                    contact = None
                    if next:
                        contact = google_obj._get_contact(next.href)
                partner_id = []
            if partner_id:
                return {
                        'name': _('Partner'),
                        'domain': "[('id','in',"+partner_id+")]",
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'res.partner',
                        'context': context,
                        'views': [(False, 'tree'),(False, 'form')],
                        'type': 'ir.actions.act_window',
                }
            else:
                return {'type': 'ir.actions.act_window_close'}   

google_contact_import()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
