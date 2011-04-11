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


import hashlib
from sugarsoap_services import *
from sugarsoap_services_types import *
from osv import osv
from tools.translate import _
import base64
from lxml import etree
class LoginError(Exception): pass

def login(username, password, url):
    loc = sugarsoapLocator()

    portType = loc.getsugarsoapPortType(url)
    request = loginRequest()
    uauth = ns0.user_auth_Def(request)
    request._user_auth = uauth

    uauth._user_name = username
    uauth._password = hashlib.md5(password).hexdigest()
    uauth._version = '1.1'
    try:
        response = portType.login(request)
    except:
        raise osv.except_osv(_('Error !'), _('Authentication error !\nBad Username or Password !'))
    if -1 == response._return._id:
        raise LoginError(response._return._error._description)
    return (portType, response._return._id)

def relation_search(portType, sessionid, module_name=None, module_id=None, related_module=None, query=None, deleted=None):
  se_req = get_relationshipsRequest()
  se_req._session = sessionid
  se_req._module_name = module_name
  se_req._module_id = module_id
  se_req._related_module =  related_module 
  se_resp = portType.get_relationships(se_req)
  ans_list = []
  if se_resp:
      list = se_resp._return.get_element_ids()
      for i in list:
          ans_list.append(i.get_element_id())
  return ans_list

def user_get_attendee_list(portType, sessionid, module_name=None, module_id=None):
  se_req = get_attendee_listRequest()
  se_req._session = sessionid
  se_req._module_name = module_name
  se_req._id = module_id
  se_resp = portType.get_attendee_list(se_req)
  list = se_resp.get_element_return()
  arch = base64.decodestring(list.Result)
  eview = False
  attende_id = False
  attende_email_id = False
  eview = etree.XML(arch)
  for child in eview:
      for ch in child.getchildren():
           if ch.tag == 'id':
               attende_id = ch.text
           if ch.tag == 'email1':
                attende_email_id = ch.text   
  return attende_id, attende_email_id            
          

def search(portType, sessionid, module_name=None):
  se_req = get_entry_listRequest()
  se_req._session = sessionid
  se_req._module_name = module_name
  se_resp = portType.get_entry_list(se_req)
  ans_list = []
  if se_resp:
      list = se_resp._return._entry_list
      for i in list:
          ans_dir = {}
          for j in i._name_value_list:
              ans_dir[j._name.encode('utf-8')] = j._value.encode('utf-8')
            #end for
          ans_list.append(ans_dir)
    #end for
  return ans_list

