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
        self.write(cr,uid,[0],{'id':1})
        #save information that you need to create the url
    def make_url():
        config_moodle = self.browse(cr, uid, ids, context=context)
        if config_moodle[0].moodle_username and config_moodle[0].moodle_password:
            url='http://'+config_moodle[0].serveur_moodle+'/moodle/webservice/xmlrpc/simpleserver.php?wsusername='+config_moodle[0].moodle_username+'&wspassword='+config_moodle[0].moodle_password
            #connexion with password and username 
        if config_moodle[0].moodle_token:
            url='http://'+config_moodle[0].serveur_moodle+'/moodle/webservice/xmlrpc/server.php?wstoken='+config_moodle[0].moodle_token
            #connexion with token 
        return url
    #create a good url for xmlrpc connect
    def create_moodle_user(self,dic_user):
        """
        user is a list of dictionaries with every required datas for moodle
        """

        sock = xmlrpclib.ServerProxy('http://127.0.0.1/moodle/webservice/xmlrpc/server.php?wstoken=3ecfb383330044a884b1ee86e0872b47')  
        #connect to moodle
    
        return sock.core_user_create_users(dic_user)
        #add user un moodle
        #return list of id and username

    def create_moodle_courses(self,courses):

        sock = xmlrpclib.ServerProxy('http://127.0.0.1/moodle/webservice/xmlrpc/server.php?wstoken=3ecfb383330044a884b1ee86e0872b47')  
        #connect to moodle
        return sock.core_course_create_courses(courses)
        #add course un moodle
                   
    def moodle_enrolled(self,enrolled):
        sock = xmlrpclib.ServerProxy('http://127.0.0.1/moodle/webservice/xmlrpc/server.php?wstoken=3ecfb383330044a884b1ee86e0872b47')  
        #connect to moodle
        sock.enrol_manual_enrol_users(enrolled)
        #add enrolled un moodle
        

        
event_moodle()

class event_event(osv.osv):
    _inherit = "event.event"
    def create_password():
        pop = string.ascii_letters + string.digits
        k=200
        while k > len(pop):
            pop *= 2
            passwd = ''.join(sample(pop, k))
        return passw
    # create a random password
        
    def button_confirm(self, cr, uid, ids, context=None):
        list_users=[]
        event = self.browse(cr, uid, ids, context=context)        
        name_event = event[0].name 
        dic_courses= [{'fullname' :name_event,'shortname' :'','categoryid':1}]
        #create a dict course
        moodle_pool = self.pool.get('event.moodle')
        response_courses = moodle_pool.create_moodle_courses(dic_courses)

        #create a course in moodle
        for registration in event[0].registration_ids:
           name_user = "moodle_"+registration.name+ "%d" % (registration.id,) #give an user name
           # to do it doesn t work if you reset the event
           dic_users={
           'username' : name_user,
           'password' : self.create_password(),
           'firstname' : registration.name , 
           'lastname': registration.name,
           'email': registration.email
           }
           #create a dictionary for an user
           list_users.append(dic_users)    
           #add the dictionary in a list        
        response_user = moodle_pool.create_moodle_user(list_users)
        #create users in moodle
        enrolled =[]
        for dic in response_user:
            enrolled=[{
            'roleid' :'1',
            'userid' :dic['id'],
            'courseid' :response_courses[0]['id']
            }]
        moodle_pool.moodle_enrolled(enrolled)
        #link a course with users
        return super(event_event, self).button_confirm(cr, uid, ids, context)

event_event()    


      
