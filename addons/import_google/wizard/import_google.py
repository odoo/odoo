try:
    import gdata
    import gdata.contacts.service
    import gdata.contacts
except ImportError:
    raise osv.except_osv(_('Google Contacts Import Error!'), _('Please install gdata-python-client from http://code.google.com/p/gdata-python-client/downloads/list'))
from import_base.import_framework import *
from import_base.mapper import *
 
class import_contact(import_framework):
    
    gd_client = False
    TABLE_CONTACT = 'contact'
    TABLE_MEETING = 'Event'
   
    def initialize(self):
        self.gd_client = gdata.contacts.service.ContactsService()
        self.gd_client.ClientLogin(self.context.get('user', False),self.context.get('password', False))

    def get_mapping(self):
        return { 
            self.TABLE_CONTACT: self.get_contact_mapping(),
        }
    def _retreive_data(self,entry):
        if entry:
            data = {}
            data['id'] = entry.id.text
            name = tools.ustr(entry.title.text)
            if name == "None":
                name = entry.email[0].address
            data['name'] = name
            emails = ','.join(email.address for email in entry.email)
            data['email'] = emails
            if entry.organization:
                if entry.organization.org_name:
                    data.update({'company': entry.organization.org_name.text})
                if entry.organization.org_title:
                    data.update ({'function': entry.organization.org_title.text})
                    
            if entry.phone_number:
                for phone in entry.phone_number:
                    if phone.rel == gdata.contacts.REL_WORK:
                        data['phone'] = phone.text
                    else:
                        data['phone'] = False
                    if phone.rel == gdata.contacts.PHONE_MOBILE:
                        data['mobile'] = phone.text
                    else : 
                        data['mobile'] = False
                    if phone.rel == gdata.contacts.PHONE_WORK_FAX:
                        data['fax'] = phone.text
                    else :
                        data['fax'] = False 
                        
            data.update({
                        'mobile': data.has_key('mobile') and data['mobile'] or False,
                        'phone':data.has_key('phone') and data['phone'] or False,
                        'fax':data.has_key('fax') and  data['fax']  or False,
                        'type':'contact',
                        'id_new':data['id'] + '_data_'+ name,
                  })
            
            
            address = {
                'name': 'name',
                'type': 'type',
                'phone': 'phone',
                'mobile': 'mobile',
                'email': 'email',
                'fax': 'fax',
            }
            return self.import_object_mapping(address,data, 'res.partner.address', 'res.partner.address',data['id_new'], self.DO_NOT_FIND_DOMAIN)

    def get_contact_mapping(self):
        contact = self.gd_client.GetContactsFeed()
        while contact:
            val = []
            for entry in contact.entry:
                val = self._retreive_data(entry)
                #val.append(self._retreive_data(entry))
            return {
            'model': 'res.partner.address',
            'import' : False,
            'dependencies': [],
            #'hook': self._retreive_data,
            'map': val
            }

