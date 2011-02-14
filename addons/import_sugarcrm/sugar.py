
import hashlib
import datetime, time
from sugarsoap_services import *
import unittest

class LoginError(Exception): pass

class SugarCRM:
    def __init__(self, url=None, tracefile=None):
        loc = sugarsoapLocator()
        self.portType = loc.getsugarsoapPortType(url=url,
                                                 tracefile=tracefile)
        self.sessid = None

    def login(self, username, password):
        request = loginRequest()
        uauth = request.new_user_auth()
        request.User_auth = uauth

        uauth.User_name = username
        uauth.Password = hashlib.md5(password).hexdigest()
        uauth.Version = "1.1"

        response = self.portType.login(request)
        if -1 == response.Return.Id:
            raise LoginError(response.Return.Error)
        self.sessid = response.Return.Id

    def logout(self):
        if None == self.sessid:
            return
        request = logoutRequest()
        request.Session = self.sessid

        self.portType.logout(request)
        self.sessid = None

    def _get_sugar_user_id(self):
        gui_req = get_user_idRequest()
        gui_req.Session = self.sessid
        uid = self.portType.get_user_id(gui_req).Return
        self.sugar_user_id = uid


    def __getattr__(self, attr):
        if "sugar_user_id" == attr:
            self._get_sugar_user_id()
            return self.sugar_user_id
        else:
            raise AttributeError

class SugarModule:
    def __init__(self, sugar, module_name,  encoding='utf-8'):
      self.module_name = module_name
      self.sugar = sugar
      self.encoding = encoding

    def search(self, entryid, fields=None):
      from sugarsoap_services  import get_entry_listRequest
      se_req = get_entry_listRequest()
      se_req._session = self.sugar.sessid
      se_req._module_name = self.module_name
      sugarcrm_obj = SugarCRM("http://localhost/sugarcrm/soap.php")
      portType = sugarcrm_obj.portType
      se_resp = portType.get_entry_list(se_req);
      list = se_resp._return._entry_list;
      ans_list = []
      for i in list:
          ans_dir = {};
          for j in i._name_value_list:
              ans_dir[j._name.encode(self.encoding)] = j._value.encode(self.encoding)
            #end for
      ans_list.append(ans_dir);
        #end for
      return ans_list;

def test(module_name):
    sugarcrm_obj = SugarCRM("http://localhost/sugarcrm/soap.php")
    sugar_login = sugarcrm_obj.login('sarah', 'sarah')
    sugarmodule_obj =  SugarModule(sugarcrm_obj, module_name)
    vals = sugarmodule_obj.search(sugarcrm_obj)
    return vals

















