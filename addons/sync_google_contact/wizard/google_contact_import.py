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

from osv import fields,osv,orm
from tools.translate import _

from sync_google_contact import sync_google_contact

class google_contact_import(osv.osv_memory):
    _name = "synchronize.base"    
    _inherit = 'synchronize.base'
    _columns = {
        'tools':  fields.selection([('gmail','Gmail')],'Tools'),
        'create_partner':fields.selection([('group','Group'),('email_address','Email address'),('gmail_user','Gmail user')], 'Create Partner'),
     }
        
    def import_contact(self, cr, uid, ids, context=None):
        # Only see the result, we will change the code
        
        addresss_obj = self.pool.get('res.partner.address')
        user_obj=self.pool.get('res.users').browse(cr, uid, uid)
        gmail_user=user_obj.gmail_user
        gamil_pwd=user_obj.gmail_password
        for obj in self.browse(cr, uid, ids, context=context):
            google_obj = sync_google_contact.google_lib(gmail_user, gamil_pwd)
            contact = google_obj._get_contact()
            addresses = []
            while contact:
                for entry in contact.entry:
                    name = entry.title.text
                    phone_numbers = ','.join(phone_number.text for phone_number in entry.phone_number)
                    emails = ','.join(email.address for email in entry.email)
                    data = {
                            'name': name,
                            'phone': phone_numbers,
                            'email': emails
                     }
                    contact_ids = addresss_obj.search(cr, uid, [('email','ilike',emails)])
                    if not contact_ids:
                        addresses.append(addresss_obj.create(cr, uid, data, context=context))
                if not contact:
                    break
                next = contact.GetNextLink()
                contact = None
                if next:
                    contact = google_obj._get_contact(next.href)
        return {
                'name': _('Contacts'),
                'domain': "[('id','in',"+str(addresses)+")]",
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'res.partner.address',
                'context': context,
                'views': [(False, 'tree'),(False, 'form')],
                'type': 'ir.actions.act_window',
        }    

google_contact_import()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
