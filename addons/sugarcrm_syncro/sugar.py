
import hashlib
from sugarsoap_services import *
from sugarsoap_services_types import *;

import sys;

class LoginError(Exception): pass

def login(username, password):
    loc = sugarsoapLocator();

    portType = loc.getsugarsoapPortType();
    request = loginRequest();
    uauth = ns0.user_auth_Def(request);
    request._user_auth = uauth;

    uauth._user_name = username;
    uauth._password = hashlib.md5(password).hexdigest();
    uauth._version = '1.1';

    response = portType.login(request);
    if -1 == response._return._id:
        raise LoginError(response._return._error._description);
    return (portType, response._return._id);

def search(portType, sessionid, module_name=None):
  se_req = get_entry_listRequest();
  se_req._session = sessionid
  se_req._module_name = module_name
  se_resp = portType.get_entry_list(se_req);
  ans_list = []
  if se_resp:
      list = se_resp._return._entry_list;
      for i in list:
          ans_dir = {};
          for j in i._name_value_list:
              ans_dir[j._name.encode('utf-8')] = j._value.encode('utf-8')
            #end for
          ans_list.append(ans_dir);
    #end for
  return ans_list;

