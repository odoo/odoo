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

from osv import fields, osv
import xmlrpclib
import string
from random import sample

class event_moodle(osv.osv):
    """ Event Type """
    _name = 'event.moodle'
    _columns = {
        'moodle_username' : fields.char('Moodle username', 128),
        'moodle_password' : fields.char('Moodle password', 128),
        'moodle_token' : fields.char('Moodle token', 128),
        'serveur_moodle': fields.char('Moodle server', 128)
    }
        
    def configure_moodle(self,cr,uid,ids,context=None):
        self.write(cr,uid,ids,{'id':1})

    def make_url(self,cr,uid,ids,context=None):
        config_moodle = self.browse(cr, uid, ids, context=context)
        if config_moodle.moodle_username and config_moodle.moodle_password:
            url='http://'+config_moodle.serveur_moodle+'/moodle/webservice/xmlrpc/simpleserver.php?wsusername='+config_moodle.moodle_username+'&wspassword='+config_moodle.moodle_password
        if config_moodle.moodle_token:
            url='http://'+config_moodle.serveur_moodle+'/moodle/webservice/xmlrpc/server.php?wstoken='+config_moodle.moodle_token
        return url

    def create_moodle_user(self,cr,uid,ids,dic_user):
        """
        user is a list of dictionaries with every required datas for moodle
        """
        sock = xmlrpclib.ServerProxy(self.make_url())  
        #connect to moodle
    
        return sock.core_user_create_users(dic_user)
        #add user un moodle
        #return list of id and username

    def create_moodle_courses(courses):
        sock = xmlrpclib.ServerProxy(self.make_url())  
        #connect to moodle
        sock.core_course_create_courses(courses)
        #add course un moodle
                   
    def moodle_enrolled(enrolled):
        sock = xmlrpclib.ServerProxy(self.Get_url())  
        #connect to moodle
        sock.enrol_manual_enrol_users(enrolled)
        #add enrolled un moodle
        

        
event_moodle()

class event_event(osv.osv):
    _inherit = "event.event"
    
    def button_confirm(self, cr, uid, ids, context=None):
        event = self.browse(cr, uid, ids, context=context)        
        name_event = event[0].name
        dic_courses= [{'fullname' :name_event,'shortname' :'','categoryid':0}]
        event_moodle.create_moodle_courses()
        return super(event_event, self).button_confirm(cr, uid, ids, context)

event_event()    


class event_registration(osv.osv):

    _inherit = "event.registration"
    
    def create_password():
        pop = string.ascii_letters + string.digits
        k=200
        while k > len(pop):
            pop *= 2
            passwd = ''.join(sample(pop, k))
        return passwd
        trhrthrthtrh
    def check_confirm(self, cr, uid, ids, context=None):
        register = self.browse(cr, uid, ids, context=context)
        users=[{
        'username' : register[0].name,
        'password' : create_password(),
        'firstname' : register[0].name, 
        'lastname': '',
        'email': register[0].email
        }]
        user=event_moodle.create_moodle_user(users)
#to do get id of the new user

        enrolled=[{
        'roleid' :'',
        'userid' :'',
        'courseid' :''
        }]
        event_moodle.moodle_enrolled(enrolled)
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        print ">>>>>>>>>>>>>>>>>>>>>>>>>>>>"
        return super(event_registration, self).check_confirm(cr, uid, ids, context)
event_registration()        
      
