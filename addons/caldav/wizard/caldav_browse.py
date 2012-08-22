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

from osv import osv, fields
from tools import config
import base64
import addons
from tools.translate import _
import tools

class caldav_browse(osv.osv_memory):

    __doc = {
    'other' : _("""
  * Webdav server that provides remote access to calendar
  * Synchronisation of calendar using WebDAV
  * Customize calendar event and todo attribute with any of OpenERP model
  * Provides iCal Import/Export functionality

    To access Calendars using CalDAV clients, point them to:
        http://HOSTNAME:PORT/webdav/DATABASE_NAME/calendars/users/USERNAME/c

    To access OpenERP Calendar using WebCal to remote site use the URL like:
        http://HOSTNAME:PORT/webdav/DATABASE_NAME/Calendars/CALENDAR_NAME.ics

      Where,
        HOSTNAME: Host on which OpenERP server(With webdav) is running
        PORT : Port on which OpenERP server is running (By Default : 8069)
        DATABASE_NAME: Name of database on which OpenERP Calendar is created
     """),

     'iphone' : _("""
    For SSL specific configuration see the documentation below

Now, to setup the calendars, you need to:

1. Click on the "Settings" and go to the "Mail, Contacts, Calendars" page.
2. Go to "Add account..."
3. Click on "Other"
4. From the "Calendars" group, select "Add CalDAV Account"

5. Enter the host's name
   (ie : if the url is http://openerp.com:8069/webdav/db_1/calendars/ , openerp.com is the host)

6. Fill Username and password with your openerp login and password

7. As a description, you can either leave the server's name or
   something like "OpenERP calendars".

9. If you are not using a SSL server, you'll get an error, do not worry and push "Continue"

10. Then click to "Advanced Settings" to specify the right
    ports and paths.

11. Specify the port for the OpenERP server: 8071 for SSL, 8069 without.

12. Set the "Account URL" to the right path of the OpenERP webdav:
    the url given by the wizard (ie : http://my.server.ip:8069/webdav/dbname/calendars/ )

11. Click on Done. The phone will hopefully connect to the OpenERP server
    and verify it can use the account.

12. Go to the main menu of the iPhone and enter the Calendar application.
    Your OpenERP calendars will be visible inside the selection of the
    "Calendars" button.
    Note that when creating a new calendar entry, you will have to specify
    which calendar it should be saved at.

IF you need SSL (and your certificate is not a verified one, as usual),
then you first will need to let the iPhone trust that. Follow these
steps:

    s1. Open Safari and enter the https location of the OpenERP server:
      https://my.server.ip:8071/
      (assuming you have the server at "my.server.ip" and the HTTPS port
      is the default 8071)
    s2. Safari will try to connect and issue a warning about the certificate
      used. Inspect the certificate and click "Accept" so that iPhone
      now trusts it.
    """),
    'android' : _("""
Prerequire
----------
There is no buit-in way to synchronize calendar with caldav.
So you need to install a third part software : Calendar (CalDav)
for now it's the only one

configuration
-------------

1. Open Calendar Sync
   I'll get an interface with 2 tabs
   Stay on the first one

2. CaDAV Calendar URL : put the URL given above (ie : http://host.com:8069/webdav/db/calendars/users/demo/c/Meetings)

3. Put your openerp username and password

4. If your server don't use SSL, you'll get a warnign, say "Yes"

5. Then you can synchronize manually or custom the settings to synchronize every x minutes.

    """),
    
     'evolution' : _("""
    1. Go to Calendar View

    2. File -> New -> Calendar

    3. Fill the form
        - type : CalDav
        - name : Whaterver you want (ie : Meeting)
        - url : http://HOST:PORT/webdav/DB_NAME/calendars/users/USER/c/Meetings (ie : http://localhost:8069/webdav/db_1/calendars/users/demo/c/Meetings) the one given on the top of this window
        - uncheck "User SSL"
        - Username : Your username (ie : Demo)
        - Refresh : everytime you want that evolution synchronize the data with the server

    4. Click ok and give your openerp password

    5. A new calendar named with the name you gave should appear on the left side.
     """),

     'thunderbird' : _("""
Prerequire
----------
If you are using thunderbird, first you need to install the lightning module
http://www.mozilla.org/projects/calendar/lightning/

configuration
-------------

1. Go to Calendar View

2. File -> New Calendar

3. Chosse "On the Network"

4. for format choose CalDav
   and as location the url given above (ie : http://host.com:8069/webdav/db/calendars/users/demo/c/Meetings)

5. Choose a name and a color for the Calendar, and we advice you to uncheck "alarm"

6. Then put your openerp login and password (to give the password only check the box "Use password Manager to remember this password"

7. Then Finish, your meetings should appear now in your calendar view
"""),
    }
    _name = 'caldav.browse'
    _description = 'Caldav Browse'

    _columns = {
        'url' : fields.char('Caldav Server', size=264, required=True, help="Url of the caldav server, use for synchronization"),
        #'doc_link':fields.char('Caldav Documentation', size="264", help="The link to Caldav Online Documentation.", readonly=True),
        'description':fields.text('Description', readonly=True)
    }

    def default_get(self, cr, uid, fields, context=None):
        pref_obj = self.pool.get('user.preference')
        pref_ids = pref_obj.browse(cr, uid ,context.get('rec_id',False), context=context)
        res = {}
        host = context.get('host')
        if not config.get_misc('webdav','enable',True):
            raise Exception("WebDAV is disabled, cannot continue.")
        user_pool = self.pool.get('res.users')
        current_user = user_pool.browse(cr, uid, uid, context=context)
        #TODO write documentation
        res['description'] = self.__doc['other']
        if pref_ids:
            pref_ids = pref_ids[0]
            if pref_ids.device == 'iphone':
                url = host + '/'+ pref_ids.service + '/' + cr.dbname + '/'+'calendars/'
            else :
                url = host + '/'+ pref_ids.service + '/' + cr.dbname + '/'+'calendars/'+ 'users/'+ current_user.login + '/'+ pref_ids.collection.name+ '/'+ pref_ids.calendar.name

            res['description'] = self.__doc.get(pref_ids.device , self.__doc['other'])
        file = open(addons.get_module_resource('caldav','doc', 'caldav_doc.pdf'),'rb')
        res['caldav_doc_file'] = base64.encodestring(file.read())

        #res['doc_link'] = 'http://doc.openerp.com/'
        res['url'] = url
        return res

    def browse_caldav(self, cr, uid, ids, context):
        return {}

caldav_browse()

class user_preference(osv.osv_memory):

    _name = 'user.preference'
    _description = 'User preference Form'

    _columns = {
               'collection' :fields.many2one('document.directory', "Calendar Collection", required=True, domain = [('calendar_collection', '=', True)]),
               'calendar' :fields.many2one('basic.calendar', 'Calendar', required=True),
               'service': fields.selection([('webdav','CalDAV')], "Services"),
               'device' : fields.selection([('other', 'Other'), ('iphone', 'iPhone'), ('android', 'Android based device'),('thunderbird', 'Sunbird/Thunderbird'), ('evolution','Evolution')], "Software/Devices"),
               'host_name': fields.char('Host Name', size=64, required=True),
    }

    def _get_default_calendar(self, cr, uid, context):
        if context == None:
            context = {}
        name = context.get('cal_name')
        collection_obj = self.pool.get('basic.calendar')
        ids = collection_obj.search(cr, uid, [('name', '=', name)])
        return ids[0]

    def _get_default_collection(self, cr, uid, context):
        collection_obj = self.pool.get('document.directory')
        ids = collection_obj.search(cr, uid, [('name', '=', 'c')])
        return ids[0]
    
    def _get_default_host(self, cr, uid, context):

        return self.pool.get('ir.config_parameter').get_param(cr, uid, 'web.base.url', default='http://localhost:8069', context=context)

    _defaults={
              'service': 'webdav',
              'collection' : _get_default_collection,
              'calendar' : _get_default_calendar,
              'device' : 'other',
              'host_name':_get_default_host

    }

    def open_window(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','caldav_Browse')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])
        context.update({'rec_id': ids})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'caldav.browse',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

    def next_window(self, cr, uid, ids, context=None):
        obj_model = self.pool.get('ir.model.data')
        host_name  = self.browse (cr,uid,ids)[0].host_name
        model_data_ids = obj_model.search(cr,uid,[('model','=','ir.ui.view'),('name','=','user_prefernce_form')])
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'])
        context.update({'res_id': ids,'host':host_name})
        resource_id = obj_model.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'user.preference',
            'views': [(resource_id,'form')],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }

user_preference()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
