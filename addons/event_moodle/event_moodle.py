# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 Tiny SPRL (<http://tiny.be>).
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
from tools.translate import _

class event_moodle(osv.osv):
    _name = 'event.moodle.config.wiz'
    _columns = {
        'moodle_username' : fields.char('Moodle Username', 128, help="You can also connect with your username that you define when you create a token"),
        'moodle_password' : fields.char('Moodle Password', 128),
        'moodle_token' : fields.char('Moodle Token', 128, help="Put your token that you created in your moodle server"),
        'server_moodle': fields.char('Moodle Server', 128, required=True,help="URL where you have your moodle server. For exemple: 'http://127.0.0.1' or 'http://localhost'"),
        'url': fields.char('URL to Moodle Server', size=256, help="The url that will be used for the connection with moodle in xml-rpc"),
    }

    _order = 'create_date desc'

    _defaults = {
        'server_moodle': 'http://127.0.0.1',
    }

    def configure_moodle(self, cr, uid, ids, context=None):
        url = self.make_url(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'url': url})
        return {'type': 'ir.actions.act_window_close'}

    def find(self, cr, uid, context=None):
        """
        Find the config wizard containing the configuration and raise and error if none is available.
        """
        moodle_config_wiz_ids = self.search(cr, uid, [], context=context)
        if not moodle_config_wiz_ids:
            raise osv.except_osv(('Error!'),("First configure your moodle connection."))
        return moodle_config_wiz_ids[0]

    def make_url(self, cr, uid, ids, context=None):
        """
        create the good url with the information of the configuration
        @return url for moodle connexion
        """
        def _encode_password(password):
            for i in range(len(password)):
                x = password[i]
                if x not in string.ascii_letters + string.digits:
                    unicode_car = (hex(ord(x)))
                    hex_car = '%'+str(unicode_car[2:])
                    password = password.replace(x,hex_car)
            return password
        url=""
        config_moodle = self.browse(cr, uid, ids[0], context=context)
        if config_moodle.moodle_username and config_moodle.moodle_password:
            #connexion with password and username
            password = _encode_password(config_moodle.moodle_password)
            url = config_moodle.server_moodle + '/moodle/webservice/xmlrpc/simpleserver.php?wsusername=' + config_moodle.moodle_username + '&wspassword=' + password
        if config_moodle.moodle_token:
            #connexion with token
            url = config_moodle.server_moodle + '/moodle/webservice/xmlrpc/server.php?wstoken=' + config_moodle.moodle_token
        return url

    def create_moodle_user(self, cr, uid, id, dic_user, context=None):
        """
        create a moodle user
        @param dic_user : is a list of dictonnaries with the moodle information
        @return a liste of dictonaries with the create user id
        """
        #connect to moodle
        url = self.browse(cr, uid, id, context=context).url
        sock = xmlrpclib.ServerProxy(url)
        #add user in moodle and return list of id and username
        return sock.core_user_create_users(dic_user)

    def create_moodle_courses(self, cr, uid, id, courses, context=None):
        """
        create a mmodle course
        @param courses : is a list of dictionaries with the moodle course information
        @return a list of dictionaries with the create course id
        """
        #connect to moodle
        url = self.browse(cr, uid, id, context=context).url
        sock = xmlrpclib.ServerProxy(url)
        return sock.core_course_create_courses(courses)

    def moodle_enrolled(self, cr, uid, id, enrolled, context=None):
        """
        this method is used to match a course with users
        @param enrolled : list of dictonaries with the course id and the user id
        """
        #connect to moodle
        url = self.browse(cr, uid, id, context=context).url
        sock = xmlrpclib.ServerProxy(url)
        #add enrolled in moodle
        sock.enrol_manual_enrol_users(enrolled)

    def create_password(self):
        """
        create a random password
        """
        rand = string.ascii_letters + string.digits
        length = 8
        passwd = ''.join(sample(rand, length))
        passwd = passwd + '+'
        return passwd

    def check_email(self,email):
    
        """
        check if email is correct
        """
        if email:
            if (email.count('@') != 1 and email.count('.') < 1):
                raise osv.except_osv(_('Error!'),_("Your email '%s' is wrong.") % (email))

    def make_username(self, username, response_courses):
        """
        create a moodle username with a random number for the uniqueness
        @return the moodle username
        """
        if username:
            #remove space in the name
            username = username.replace(" ","_")
            #give an user name
            name_user = username + "%d" % (response_courses,) + "%d" % (random.randint(1,999999),)
        else:
            name_user = "moodle_" + "%d" % (response_courses,) + "%d" % (random.randint(1,999999),)
        return name_user

event_moodle()

class event_event(osv.osv):
    _inherit = "event.event"

    _columns={
        'moodle_id': fields.integer('Moodle ID', help='The identifier of this event in Moodle'),
    }

    def check_registration_limits(self, cr, uid, ids, context=None):
        """
        create moodle courses ,users and match them when an event is confirmed
        if the event_registration is not confirmed then it doesn t nothing
        """
        res = super(event_event, self).check_registration_limits(cr, uid, ids, context=context)
        moodle_pool = self.pool.get('event.moodle.config.wiz')
        moodle_config_wiz_id = moodle_pool.find(cr, uid, context=context)
        list_users=[]
        userid = []
        for event in self.browse(cr, uid, ids, context=context):
            #moodle use time() to store the date
            date = time.strptime(event.date_begin, '%Y-%m-%d %H:%M:%S')
            date = int (time.mktime(date))
            #create the dict of values to create the course in Moodle
            dic_courses= [{
                'fullname': event.name,
                'shortname': '',
                'startdate': date,
                'summary': event.note,
                'categoryid':1, #the category hardcoded is 'Miscellaneous'
                }]
            #create a course in moodle and keep the id
            response_courses = moodle_pool.create_moodle_courses(cr, uid, moodle_config_wiz_id, dic_courses, context=context)
            self.write(cr, uid, event.id, {'moodle_id': response_courses[0]['id']})

            moodle_uids = []
            for registration in event.registration_ids:
                if registration.state == 'open':
                    #enroll the registration in Moodle as it is confirmed
                    if not registration.moodle_uid:
                        #create a dictionary for an user
                        name_user = moodle_pool.make_username(registration.name, response_courses[0]['id'])
                        moodle_pool.check_email(registration.email)
                        passwd = moodle_pool.create_password()
                        dic_users={
                            'username' : name_user,
                            'password' : passwd,
                            'city' : registration.city,
                            'firstname' : registration.name ,
                            'lastname': '',
                            'email': registration.email
                        }
                        #create the user in moodle
                        response_user = moodle_pool.create_moodle_user(cr, uid, moodle_config_wiz_id, [dic_users], context=context)
                        for user in response_user:
                            self.pool.get('event.registration').write(cr,uid,[registration.id],{'moodle_uid': user['id'], 'moodle_user_password': passwd, 'moodle_username': name_user})
                            moodle_uids.append(user['id'])
                    else:
                        moodle_uids.append(registration.moodle_uid)

            #link the course with users
            enrolled = []
            for moodle_user in moodle_uids:
                enrolled.append({
                'roleid' :'5', #mark as 'Student'
                'userid' : moodle_user,
                'courseid' :response_courses[0]['id']
                })
            moodle_pool.moodle_enrolled(cr, uid, moodle_config_wiz_id, enrolled, context=context)
        return res

event_event()

class event_registration(osv.osv):

    _inherit = "event.registration"

    _columns={
        'moodle_user_password': fields.char('Password for Moodle User', 128),
        'moodle_username': fields.char('Moodle Username', 128),
        'moodle_uid': fields.integer('Moodle User ID'),
    }

    def confirm_registration(self, cr, uid, ids, context=None):
        """
        create a user and match to a course if the event is already confirmed
        """
        res = super(event_registration, self).confirm_registration(cr, uid, ids, context=context)
        moodle_pool = self.pool.get('event.moodle.config.wiz')
        moodle_config_wiz_id = moodle_pool.find(cr, uid, context=context)
        for register in self.browse(cr, uid, ids, context=context):
            if register.event_id.state == 'confirm' and register.event_id.moodle_id:
                if not register.moodle_uid:
                    #create the user in moodle
                    name_user = moodle_pool.make_username(register.name, register.event_id.moodle_id)
                    moodle_pool.check_email(register.email)
                    passwd = moodle_pool.create_password()
                    dic_users = [{
                        'username': name_user,
                        'password': passwd,
                        'city': register.city,
                        'firstname': register.name,
                        'lastname': '', #we could make a split of the register.name on ' ' but it would be inaccurate, so it seems better to let it empty as it's not really useful
                        'email': register.email,
                    }]
                    response_user = moodle_pool.create_moodle_user(cr, uid, moodle_config_wiz_id, dic_users, context=context)
                    #write in database the password and the username
                    moodle_user_id = response_user[0]['id']
                    self.pool.get('event.registration').write(cr, uid, ids, {'moodle_uid': moodle_user_id, 'moodle_user_password': passwd, 'moodle_username': name_user})
                else:
                    moodle_user_id = register.moodle_uid
                enrolled=[{
                    'roleid': '5', #mark as student
                    'userid': moodle_user_id,
                    'courseid': register.event_id.moodle_id
                }]
                moodle_pool.moodle_enrolled(cr, uid, moodle_config_wiz_id, enrolled, context=context)
        return res

    def onchange_moodle_name(self, cr, uid, ids, moodle_username, context=None):
        """
        This onchange receive as parameter a username moddle and will fill the moodle_uid and password fields if existing records with this username are found
            @param moodle_username: the existing moodle username
        """
        res = {}
        reg_ids = self.search(cr, uid, [('moodle_username', '=', moodle_username)], order='create_date desc', context=context)
        if reg_ids:
            reg = self.browse(cr, uid, reg_ids[0], context=context)
            res = {'value' :{
                    'moodle_uid': reg.moodle_uid,
                    'name': reg.name,
                    'email':reg.email,
                    'phone':reg.phone,
                    'city': reg.city,
                    'street': reg.street}}
        return res
event_registration()
