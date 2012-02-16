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


class event_moodle(osv.osv):
    """ Event Type """
    _name = 'event.moodle'
    _inherit = 'event.registration'
    _columns = {
        'moodle_ok' : fields.boolean('moodle_ok'),
        'moodle_username' : fields.char('Moodle username', 128),
        'moodle_password' : fields.char('Moodle password', 128),
        'moodle_token' : fields.char('Moodle token', 128),
        'serveur_moodle': fields.char('Moodle token', 128),
    }


def Get_url():
    """
    attr: 
    serveur_moodle
    token
    password
    username
    """
    hostname="127.0.0.1"
    password="Administrateur1%2b"
    username="admin"
    
    #if token
    token='3ecfb383330044a884b1ee86e0872b47'
    url='http://'+hostname+'/moodle/webservice/xmlrpc/server.php?wstoken='+token
    #if user connect
    url='http://'+hostname+'/moodle/webservice/xmlrpc/simpleserver.php?wsusername='+username+'&wspassword='+password
    return url
    
def create_moodle_user():
    #user is a list of dictionaries with every required datas for moodle
    users=[{
    'username' : 'efegt(gtrhf',
    'password' : 'Azertyui1+',
    'firstname' : 'res', 
    'lastname': 'ezr',
    'email': 'gegtr@ggtr.com'
    }]

    #connect to moodle
    sock = xmlrpclib.ServerProxy(self.Get_url())  
    
    #add user un moodle
    return sock.core_user_create_users(users)
    
    #return list of id and username
    
def create_moodle_courses():
    courses=[{
    'fullname' :'',
    'shortname' :'',
    'categoryid':''
    }]
    #connect to moodle
    sock = xmlrpclib.ServerProxy(self.Get_url())  
    
    #add course un moodle
    sock.core_course_create_courses(courses)

def moodleenrolled():
    enrolled=[{
    'roleid' :'',
    'userid' :'',
    'courseid' :''
    }]
    #connect to moodle
    sock = xmlrpclib.ServerProxy(self.Get_url())  
    
    #add enrolled un moodle
    sock.enrol_manual_enrol_users(enrolled)
    
event_moodle()
