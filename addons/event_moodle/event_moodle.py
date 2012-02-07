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
import time
import random
from random import sample

class event_moodle(osv.osv):
    """ Event Type """
    _name = 'event.moodle'
    _columns = {
        'moodle_username' : fields.char('Moodle username', 128,help="You can also connect with your username that you define when you create a tokken"),
        'moodle_password' : fields.char('Moodle password', 128),
        'moodle_token' : fields.char('Moodle token', 128,help="Put your token that you created in your moodle serveur"),
        'serveur_moodle': fields.char('Moodle server', 128, required=True,help="URL where you have your moodle server ")
    }

    url=''
    def configure_moodle(self,cr,uid,ids,context=None):
        """
        Use to configure moodle
        """
        self.write(cr,uid,[1],{'id':1})
        #save information that you need to create the url
        return {'type': 'ir.actions.act_window_close'}
        #use to quit the wizard

    def make_url(self,cr,uid,ids,context=None):
        """
        create the good url with the information of the configuration
        @return url for moodle connexion
        """
        config_moodle = self.browse(cr, uid, ids, context=context)
        if config_moodle[0].moodle_username and config_moodle[0].moodle_password:
            url='http://'+config_moodle[0].serveur_moodle+'/moodle/webservice/xmlrpc/simpleserver.php?wsusername='+config_moodle[0].moodle_username+'&wspassword='+config_moodle[0].moodle_password
            #connexion with password and username
            #to do warning on special char
        if config_moodle[0].moodle_token:
            url='http://'+config_moodle[0].serveur_moodle+'/moodle/webservice/xmlrpc/server.php?wstoken='+config_moodle[0].moodle_token
            #connexion with token
        self.url = url
        return url
    #create a good url for xmlrpc connect

    def create_moodle_user(self,cr,uid,ids,dic_user):
        """
        create a moodle user
        @param dic_user : is a list of dictonnaries with the moodle information
        @return a liste of dictonaries with the create user id
        """
        self.make_url(cr,uid,ids,context=None)
        sock = xmlrpclib.ServerProxy(self.url)
        #connect to moodle
        return sock.core_user_create_users(dic_user)
        #add user un moodle and return list of id and username

    def create_moodle_courses(self,cr,uid,ids,courses):
        """
        create a mmodle course
        @param courses : is a list of dictionaries with the moodle course information
        @return a list of dictionaries with the create course id
        """
        self.make_url(cr,uid,ids,context=None)
        sock = xmlrpclib.ServerProxy(self.url)
        #connect to moodle
        return sock.core_course_create_courses(courses)
        #add course un moodle

    def moodle_enrolled(self,cr,uid,ids,enrolled):
        """
        this method is used to match a course with users
        @param enrolled : list of dictonaries with the course id and the user id
        """
        self.make_url(cr,uid,ids,context=None)
        sock = xmlrpclib.ServerProxy(self.url)
        #connect to moodle
        sock.enrol_manual_enrol_users(enrolled)
        #add enrolled un moodle

    def create_password(self):
        """
        create a random password
        """
        rand = string.ascii_letters + string.digits
        length=8
        while length > len(rand):
            rand *= 2
        passwd = ''.join(sample(rand, length))
        passwd = passwd+'+'
        return passwd
        # create a random password
    def check_email(self,email):
        """
        check is email is true
        """
        if email:
            if (email.count('@')!=1 and email.count('.')<1):
                    raise osv.except_osv(_('Error!'),_("Your email '%s' is wrong") % (email))

    def make_username(self,username,response_courses):
        """
        create a moodle username with a random number for the uniqueness
        @return the moodle username
        """
        if username:
            username=username.replace(" ","_")
                   #remove space in the name
            name_user = username+"%d" % (response_courses,)+ "%d" % (random.randint(1,999999),)
               #give an user name
        else:
            name_user = "moodle_"+"%d" % (response_courses,)+ "%d" % (random.randint(1,999999),)
        return name_user

event_moodle()


class event_event(osv.osv):
    _inherit = "event.event"
    _columns={
    'moodle_id' :fields.integer('Moodle id'),
    }
    def button_confirm(self, cr, uid, ids, context=None):
        """
        create moodle courses ,users and match them when an event is confirmed
        if the event_registration is not confirmed then it doesn t nothing
        """
        list_users=[]
        userid = []
        event = self.browse(cr, uid, ids, context=context)
        name_event = event[0].name
        date = event[0].date_begin
        date=time.strptime(date,'%Y-%m-%d %H:%M:%S')
        date = int (time.mktime(date))
        #moodle use time() to store the date
        dic_courses= [{'fullname' :name_event,'shortname' :'','startdate':date,'summary':event[0].note,'categoryid':1}]
        #create a dict course
        moodle_pool = self.pool.get('event.moodle')
        response_courses = moodle_pool.create_moodle_courses(cr,uid,[1],dic_courses)
        self.write(cr,uid,ids,{'moodle_id':response_courses[0]['id']})
        #create a course in moodle and keep the id
        for registration in event[0].registration_ids:
           name_user=moodle_pool.make_username(registration.name,response_courses[0]['id'])
           moodle_pool.check_email(registration.email)
           passwd=moodle_pool.create_password()
           if registration.state=='open':
           #confirm if the registrator is confirmed
               if registration.moodle_users_id == 0:
                   dic_users={
                   'username' : name_user,
                   'password' : passwd,
                   'city' : registration.city,
                   'firstname' : registration.name ,
                   'lastname': '',
                   'email': registration.email
                   }
                   #create a dictionary for an user
                   list_users.append(dic_users)
                   #add the dictionary in a list 
               else:
                   userid = []
                   userid.append(registration.moodle_users_id)
        response_user = moodle_pool.create_moodle_user(cr,uid,[1],list_users)
        #create users in moodle
        enrolled =[]

        for list in userid:
            self.pool.get('event.registration').write(cr,uid,[registration.id],{'moodle_users_id':list,'moodle_user_password':passwd,'moodle_users':name_user})
            #write in database the password and the username and the id
            enrolled=[{
            'roleid' :'5',
            'userid' :list,
            'courseid' :response_courses[0]['id']
            }]
            moodle_pool.moodle_enrolled(cr,uid,[1],enrolled)
            #link a course with users


        for dic in response_user:
            self.pool.get('event.registration').write(cr,uid,[registration.id],{'moodle_users_id':dic['id'],'moodle_user_password':passwd,'moodle_users':name_user})
            #write in database the password and the username and the id
            enrolled=[{
            'roleid' :'5',
            'userid' :dic['id'],
            'courseid' :response_courses[0]['id']
            }]
            moodle_pool.moodle_enrolled(cr,uid,[1],enrolled)
            #link a course with users
        return super(event_event, self).button_confirm(cr, uid, ids, context)

event_event()

class event_registration(osv.osv):
    _inherit = "event.registration"
    _columns={
    'moodle_user_password': fields.char('password for moodle user', 128),
    'moodle_users': fields.char('moodle username', 128),
    'moodle_users_id': fields.integer('moodle uid'),
    'moodle_check_user':fields.char('Moodle username',128,help='Try to find an existing username')
    }
    _defaults={
    'moodle_check_user':''
    }
    def case_open(self, cr, uid, ids, context=None):
        """
        create a user and match to a course if the event is already confirmed
        """
        register = self.browse(cr, uid, ids, context=context)
        if register[0].event_id.state =='confirm': 
            moodle_pool = self.pool.get('event.moodle')
            print 
            if register[0].moodle_users_id ==0:
                moodle_pool = self.pool.get('event.moodle')
                name_user = moodle_pool.make_username(register[0].name,register[0].event_id.moodle_id)
                passwd=moodle_pool.create_password()
                dic_users=[{
                'username' : name_user,
                'password' : passwd,
                'city' : register[0].city,
                'firstname' : register[0].name,
                'lastname': '',
                'email': register[0].email
                }]
                #create a dictionary for an use
                response_user = moodle_pool.create_moodle_user(cr,uid,[1],dic_users)
                self.pool.get('event.registration').write(cr,uid,ids,{'moodle_users_id':response_user[0]['id'],'moodle_user_password':passwd,'moodle_users':name_user})
                #write in database the password and the username
                enrolled=[{
                'roleid' :'5',
                'userid' :response_user[0]['id'],#use the response of the create user
                'courseid' :register[0].event_id.moodle_id
                }]
            else:
                enrolled=[{
                'roleid' :'5',
                'userid' :register[0].moodle_users_id,
                'courseid' :register[0].event_id.moodle_id
                }]

            print enrolled
            print'>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>'
            moodle_pool.moodle_enrolled(cr,uid,[1],enrolled)
        return super(event_registration, self).check_confirm(cr, uid, ids, context)


    def onchange_moodle_name(self,cr,uid,ids,moodle_check_user,context=None):
        req_sql="select moodle_users,moodle_users_id from event_registration"
        cr.execute(req_sql)
        sql_res = cr.dictfetchall()
        res = {}
        username_id = 0
        for username in sql_res:
            if username['moodle_users'] == moodle_check_user:
               username_id=username['moodle_users_id']
               res = {'value' :{'moodle_users_id': username_id}}
            else:
               res = {'value' :{'moodle_users_id': 0}}
        return res


















