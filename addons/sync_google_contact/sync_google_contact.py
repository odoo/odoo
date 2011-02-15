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

try:
    import gdata
    from gdata import contacts
    import gdata.contacts.service
    import atom
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))

class google_lib(object):

    def __init__(self, email, password):
        super(google_lib, self).__init__()
        self.contact = gdata.contacts.service.ContactsService()
        self.contact.email = email
        self.contact.password = password
        self.contact.source = 'OpenERP'
        try:
            self.contact.ProgrammaticLogin()
        except Exception, e:
            raise osv.except_osv(_('Error!'),_('%s' % (e)))
        
    def _get_contact(self, href=''):
        if href:
            feed = self.contact.GetContactsFeed(href)
        else:
            feed = self.contact.GetContactsFeed()
        return feed

    def _get_contact_allGroups(self):
         """  fetch all allGroup."""
         feed = self.contact.GetGroupsFeed()
         return feed        
    def _create_contact(self,name,primary_email):
        """  create a contact."""
    
        new_contact = gdata.contacts.ContactEntry(title=atom.Title(text=name))
        # Create a work email address for the contact and use as primary. 
        if primary_email:
            new_contact.email.append(gdata.contacts.Email(address=primary_email, 
            primary='true', rel=gdata.contacts.REL_WORK))
        entry = self.contact.CreateContact(new_contact)
        return entry
    def _delete_contact(self):
        self.contact.DeleteContact(selected_entry.GetEditLink().href)        
        return True

class res_partner_address(osv.osv):
    
    _inherit = "res.partner.address"
    _columns = {
        'sync_google':fields.boolean('Synchronize with Google'),   
        'google_id': fields.char('Google Contact Id', size=128, readonly=True),  
    }    
    

    def create(self, cr, uid, vals, context=None):
        id =super(res_partner_address, self).create(cr, uid, vals, context=context)  
        vals.update({'ids':id})
        if context is None:
            context = {}
        if vals.get('sync_google') :
            self.sync_create(cr,uid,vals,context=context,synchronize=vals.get('sync_google'))
        return id

    def write(self, cr, uid, ids, vals, context=None, check=True, update_check=True):
        if context is None:
            context = {}
        return super(res_partner_address, self).write(cr, uid, ids, vals, context=context)
        
    def sync_create(self, cr, uid, vals, context=None,synchronize=True):
        # we all more detail soon
        user_obj=self.pool.get('res.users').browse(cr, uid, uid)
        gmail_user=user_obj.gmail_user
        gamil_pwd=user_obj.gmail_password
        google_obj =google_lib(gmail_user, gamil_pwd)
        name=vals.get('name')
        email=vals.get('email')
        contact = google_obj._create_contact(name,email) 
        openerp_id=vals['ids']
        self.write(cr,uid,[openerp_id],{'google_id':contact.id.text},context=context)
        return True
res_partner_address()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

