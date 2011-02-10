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

try:
    import gdata
    from gdata import  contacts
    import gdata.contacts.service
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

class google_lib(object):

    def __init__(self, email, password):
        super(google_lib, self).__init__()
        self.contact = gdata.contacts.service.ContactsService()
        self.contact.email = email
        self.contact.password = password
        self.contact.source = 'GoogleInc-ContactsPythonSample-1'
        self.contact.ProgrammaticLogin()
        
    def _get_contact(self):
        feed= self.contact.GetContactsFeed()
        return feed

    def _get_contact_allGroups(self):
         """  fetch all allGroup."""
         feed = self.contact.GetGroupsFeed()
         return feed        
    def _create_contact(self,name,primary_email):
        """  create a contact."""
    
        new_contact = gdata.contacts.ContactEntry(title=atom.Title(text=name))
        # Create a work email address for the contact and use as primary. 
        new_contact.email.append(gdata.contacts.Email(address=primary_email, 
            primary='true', rel=gdata.contacts.REL_WORK))
        entry = self.contact.CreateContact(new_contact)
        return entry
    def _delete_contact(self):
        self.contact.DeleteContact(selected_entry.GetEditLink().href)        
        return True

class google_contact(osv.osv):
    _description ='Google Contact'
    _name = 'google.contact'
    _columns = {
        'user': fields.char('Login', size=64, required=True,),
        'password': fields.char('Password', size=64,),
        }
    def get_contact(self, cr, uid, ids, context):
        # Only see the result , we will change the code
        for obj in self.browse(cr, uid, ids, context=context):
            google_obj=google_lib(obj.user,obj.password)
            contact=google_obj._get_contact()
            while contact:
                for i, contact in enumerate(contact.entry):
                    if contact.title.text:
                        print contact.title.text
                next = contact.GetNextLink()
                contact=None
                if next:
                    contact = google_obj.GetContactsFeed(next.href)
        return {}    
google_contact()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

