"""
ldapobject.py - wraps class _ldap.LDAPObject

See https://www.python-ldap.org/ for details.
"""
from os import strerror

from ldap.pkginfo import __version__, __author__, __license__

__all__ = [
  'LDAPObject',
  'SimpleLDAPObject',
  'ReconnectLDAPObject',
  'LDAPBytesWarning'
]


if __debug__:
  # Tracing is only supported in debugging mode
  import traceback

import sys,time,pprint,_ldap,ldap,ldap.sasl,ldap.functions
import warnings

from ldap.schema import SCHEMA_ATTRS
from ldap.controls import LDAPControl,DecodeControlTuples,RequestControlTuples
from ldap.extop import ExtendedRequest,ExtendedResponse,PasswordModifyResponse

from ldap import LDAPError


class LDAPBytesWarning(BytesWarning):
    """Python 2 bytes mode warning"""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "LDAPBytesWarning is deprecated and will be removed in the future",
            DeprecationWarning,
        )
        super().__init__(*args, **kwargs)


class NO_UNIQUE_ENTRY(ldap.NO_SUCH_OBJECT):
  """
  Exception raised if a LDAP search returned more than entry entry
  although assumed to return a unique single search result.
  """


class SimpleLDAPObject:
  """
  This basic class wraps all methods of the underlying C API object.

  The arguments are same as for the :func:`~ldap.initialize()` function.
  """

  CLASSATTR_OPTION_MAPPING = {
    "protocol_version":   ldap.OPT_PROTOCOL_VERSION,
    "deref":              ldap.OPT_DEREF,
    "referrals":          ldap.OPT_REFERRALS,
    "timelimit":          ldap.OPT_TIMELIMIT,
    "sizelimit":          ldap.OPT_SIZELIMIT,
    "network_timeout":    ldap.OPT_NETWORK_TIMEOUT,
    "error_number":ldap.OPT_ERROR_NUMBER,
    "error_string":ldap.OPT_ERROR_STRING,
    "matched_dn":ldap.OPT_MATCHED_DN,
  }

  def __init__(
    self,uri,
    trace_level=0,trace_file=None,trace_stack_limit=5,bytes_mode=None,
    bytes_strictness=None, fileno=None
  ):
    self._trace_level = trace_level or ldap._trace_level
    self._trace_file = trace_file or ldap._trace_file
    self._trace_stack_limit = trace_stack_limit
    self._uri = uri
    self._ldap_object_lock = self._ldap_lock('opcall')
    if fileno is not None:
      if not hasattr(_ldap, "initialize_fd"):
        raise ValueError("libldap does not support initialize_fd")
      if hasattr(fileno, "fileno"):
        fileno = fileno.fileno()
      self._l = ldap.functions._ldap_function_call(
        ldap._ldap_module_lock, _ldap.initialize_fd, fileno, uri
      )
    else:
      self._l = ldap.functions._ldap_function_call(ldap._ldap_module_lock,_ldap.initialize,uri)
    self.timeout = -1
    self.protocol_version = ldap.VERSION3

    if bytes_mode:
        raise ValueError("bytes_mode is *not* supported under Python 3.")

  @property
  def bytes_mode(self):
    return False

  @property
  def bytes_strictness(self):
    return 'error'

  def _ldap_lock(self,desc=''):
    if ldap.LIBLDAP_R:
      return ldap.LDAPLock(desc='%s within %s' %(desc,repr(self)))
    else:
      return ldap._ldap_module_lock

  def _ldap_call(self,func,*args,**kwargs):
    """
    Wrapper method mainly for serializing calls into OpenLDAP libs
    and trace logs
    """
    self._ldap_object_lock.acquire()
    if __debug__:
      if self._trace_level>=1:
        self._trace_file.write('*** {} {} - {}\n{}\n'.format(
          repr(self),
          self._uri,
          '.'.join((self.__class__.__name__,func.__name__)),
          pprint.pformat((args,kwargs))
        ))
        if self._trace_level>=9:
          traceback.print_stack(limit=self._trace_stack_limit,file=self._trace_file)
    diagnostic_message_success = None
    try:
      try:
        result = func(*args,**kwargs)
        if __debug__ and self._trace_level>=2:
          if func.__name__!="unbind_ext":
            diagnostic_message_success = self._l.get_option(ldap.OPT_DIAGNOSTIC_MESSAGE)
      finally:
        self._ldap_object_lock.release()
    except LDAPError as e:
      try:
        if 'info' not in e.args[0] and 'errno' in e.args[0]:
          e.args[0]['info'] = strerror(e.args[0]['errno'])
      except IndexError:
        pass
      if __debug__ and self._trace_level>=2:
        self._trace_file.write('=> LDAPError - {}: {}\n'.format(e.__class__.__name__,str(e)))
      raise
    else:
      if __debug__ and self._trace_level>=2:
        if not diagnostic_message_success is None:
          self._trace_file.write('=> diagnosticMessage: %s\n' % (repr(diagnostic_message_success)))
        self._trace_file.write('=> result:\n%s\n' % (pprint.pformat(result)))
    return result

  def __setattr__(self,name,value):
    if name in self.CLASSATTR_OPTION_MAPPING:
      self.set_option(self.CLASSATTR_OPTION_MAPPING[name],value)
    else:
      self.__dict__[name] = value

  def __getattr__(self,name):
    if name in self.CLASSATTR_OPTION_MAPPING:
      return self.get_option(self.CLASSATTR_OPTION_MAPPING[name])
    elif name in self.__dict__:
      return self.__dict__[name]
    else:
      raise AttributeError('{} has no attribute {}'.format(
        self.__class__.__name__,repr(name)
      ))

  def fileno(self):
    """
    Returns file description of LDAP connection.

    Just a convenience wrapper for LDAPObject.get_option(ldap.OPT_DESC)
    """
    return self.get_option(ldap.OPT_DESC)

  def abandon_ext(self,msgid,serverctrls=None,clientctrls=None):
    """
    abandon_ext(msgid[,serverctrls=None[,clientctrls=None]]) -> None
    abandon(msgid) -> None
        Abandons or cancels an LDAP operation in progress. The msgid should
        be the message id of an outstanding LDAP operation as returned
        by the asynchronous methods search(), modify() etc.  The caller
        can expect that the result of an abandoned operation will not be
        returned from a future call to result().
    """
    return self._ldap_call(self._l.abandon_ext,msgid,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def abandon(self,msgid):
    return self.abandon_ext(msgid,None,None)

  def cancel(self,cancelid,serverctrls=None,clientctrls=None):
    """
    cancel(cancelid[,serverctrls=None[,clientctrls=None]]) -> int
        Send cancels extended operation for an LDAP operation specified by cancelid.
        The cancelid should be the message id of an outstanding LDAP operation as returned
        by the asynchronous methods search(), modify() etc.  The caller
        can expect that the result of an abandoned operation will not be
        returned from a future call to result().
        In opposite to abandon() this extended operation gets an result from
        the server and thus should be preferred if the server supports it.
    """
    return self._ldap_call(self._l.cancel,cancelid,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def cancel_s(self,cancelid,serverctrls=None,clientctrls=None):
    msgid = self.cancel(cancelid,serverctrls,clientctrls)
    try:
      res = self.result(msgid,all=1,timeout=self.timeout)
    except (ldap.CANCELLED,ldap.SUCCESS):
      res = None
    return res

  def add_ext(self,dn,modlist,serverctrls=None,clientctrls=None):
    """
    add_ext(dn, modlist[,serverctrls=None[,clientctrls=None]]) -> int
        This function adds a new entry with a distinguished name
        specified by dn which means it must not already exist.
        The parameter modlist is similar to the one passed to modify(),
        except that no operation integer need be included in the tuples.
    """
    return self._ldap_call(self._l.add_ext,dn,modlist,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def add_ext_s(self,dn,modlist,serverctrls=None,clientctrls=None):
    msgid = self.add_ext(dn,modlist,serverctrls,clientctrls)
    resp_type, resp_data, resp_msgid, resp_ctrls = self.result3(msgid,all=1,timeout=self.timeout)
    return resp_type, resp_data, resp_msgid, resp_ctrls

  def add(self,dn,modlist):
    """
    add(dn, modlist) -> int
        This function adds a new entry with a distinguished name
        specified by dn which means it must not already exist.
        The parameter modlist is similar to the one passed to modify(),
        except that no operation integer need be included in the tuples.
    """
    return self.add_ext(dn,modlist,None,None)

  def add_s(self,dn,modlist):
    return self.add_ext_s(dn,modlist,None,None)

  def simple_bind(self,who=None,cred=None,serverctrls=None,clientctrls=None):
    """
    simple_bind([who='' [,cred='']]) -> int
    """
    return self._ldap_call(self._l.simple_bind,who,cred,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def simple_bind_s(self,who=None,cred=None,serverctrls=None,clientctrls=None):
    """
    simple_bind_s([who='' [,cred='']]) -> 4-tuple
    """
    msgid = self.simple_bind(who,cred,serverctrls,clientctrls)
    resp_type, resp_data, resp_msgid, resp_ctrls = self.result3(msgid,all=1,timeout=self.timeout)
    return resp_type, resp_data, resp_msgid, resp_ctrls

  def bind(self,who,cred,method=ldap.AUTH_SIMPLE):
    """
    bind(who, cred, method) -> int
    """
    assert method==ldap.AUTH_SIMPLE,'Only simple bind supported in LDAPObject.bind()'
    return self.simple_bind(who,cred)

  def bind_s(self,who,cred,method=ldap.AUTH_SIMPLE):
    """
    bind_s(who, cred, method) -> None
    """
    msgid = self.bind(who,cred,method)
    return self.result(msgid,all=1,timeout=self.timeout)

  def sasl_interactive_bind_s(self,who,auth,serverctrls=None,clientctrls=None,sasl_flags=ldap.SASL_QUIET):
    """
    sasl_interactive_bind_s(who, auth [,serverctrls=None[,clientctrls=None[,sasl_flags=ldap.SASL_QUIET]]]) -> None
    """
    return self._ldap_call(self._l.sasl_interactive_bind_s,who,auth,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls),sasl_flags)

  def sasl_non_interactive_bind_s(self,sasl_mech,serverctrls=None,clientctrls=None,sasl_flags=ldap.SASL_QUIET,authz_id=''):
    """
    Send a SASL bind request using a non-interactive SASL method (e.g. GSSAPI, EXTERNAL)
    """
    auth = ldap.sasl.sasl(
      {ldap.sasl.CB_USER:authz_id},
      sasl_mech
    )
    self.sasl_interactive_bind_s('',auth,serverctrls,clientctrls,sasl_flags)

  def sasl_external_bind_s(self,serverctrls=None,clientctrls=None,sasl_flags=ldap.SASL_QUIET,authz_id=''):
    """
    Send SASL bind request using SASL mech EXTERNAL
    """
    self.sasl_non_interactive_bind_s('EXTERNAL',serverctrls,clientctrls,sasl_flags,authz_id)

  def sasl_gssapi_bind_s(self,serverctrls=None,clientctrls=None,sasl_flags=ldap.SASL_QUIET,authz_id=''):
    """
    Send SASL bind request using SASL mech GSSAPI
    """
    self.sasl_non_interactive_bind_s('GSSAPI',serverctrls,clientctrls,sasl_flags,authz_id)

  def sasl_bind_s(self,dn,mechanism,cred,serverctrls=None,clientctrls=None):
    """
    sasl_bind_s(dn, mechanism, cred [,serverctrls=None[,clientctrls=None]]) -> int|str
    """
    return self._ldap_call(self._l.sasl_bind_s,dn,mechanism,cred,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def compare_ext(self,dn,attr,value,serverctrls=None,clientctrls=None):
    """
    compare_ext(dn, attr, value [,serverctrls=None[,clientctrls=None]]) -> int
    compare_ext_s(dn, attr, value [,serverctrls=None[,clientctrls=None]]) -> bool
    compare(dn, attr, value) -> int
    compare_s(dn, attr, value) -> bool
        Perform an LDAP comparison between the attribute named attr of entry
        dn, and the value value. The synchronous form returns True or False.
        The asynchronous form returns the message id of the initiates request,
        and the result of the asynchronous compare can be obtained using
        result().

        Note that this latter technique yields the answer by raising
        the exception objects COMPARE_TRUE or COMPARE_FALSE.

        A design bug in the library prevents value from containing
        nul characters.
    """
    return self._ldap_call(self._l.compare_ext,dn,attr,value,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def compare_ext_s(self,dn,attr,value,serverctrls=None,clientctrls=None):
    msgid = self.compare_ext(dn,attr,value,serverctrls,clientctrls)
    try:
        ldap_res = self.result3(msgid,all=1,timeout=self.timeout)
    except ldap.COMPARE_TRUE:
      return True
    except ldap.COMPARE_FALSE:
      return False
    raise ldap.PROTOCOL_ERROR(
        f'Compare operation returned wrong result: {ldap_res!r}'
    )

  def compare(self,dn,attr,value):
    return self.compare_ext(dn,attr,value,None,None)

  def compare_s(self,dn,attr,value):
    return self.compare_ext_s(dn,attr,value,None,None)

  def delete_ext(self,dn,serverctrls=None,clientctrls=None):
    """
    delete(dn) -> int
    delete_s(dn) -> None
    delete_ext(dn[,serverctrls=None[,clientctrls=None]]) -> int
    delete_ext_s(dn[,serverctrls=None[,clientctrls=None]]) -> tuple
        Performs an LDAP delete operation on dn. The asynchronous
        form returns the message id of the initiated request, and the
        result can be obtained from a subsequent call to result().
    """
    return self._ldap_call(self._l.delete_ext,dn,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def delete_ext_s(self,dn,serverctrls=None,clientctrls=None):
    msgid = self.delete_ext(dn,serverctrls,clientctrls)
    resp_type, resp_data, resp_msgid, resp_ctrls = self.result3(msgid,all=1,timeout=self.timeout)
    return resp_type, resp_data, resp_msgid, resp_ctrls

  def delete(self,dn):
    return self.delete_ext(dn,None,None)

  def delete_s(self,dn):
    return self.delete_ext_s(dn,None,None)

  def extop(self,extreq,serverctrls=None,clientctrls=None):
    """
    extop(extreq[,serverctrls=None[,clientctrls=None]]]) -> int
    extop_s(extreq[,serverctrls=None[,clientctrls=None[,extop_resp_class=None]]]]) ->
        (respoid,respvalue)
        Performs an LDAP extended operation. The asynchronous
        form returns the message id of the initiated request, and the
        result can be obtained from a subsequent call to extop_result().
        The extreq is an instance of class ldap.extop.ExtendedRequest.

        If argument extop_resp_class is set to a sub-class of
        ldap.extop.ExtendedResponse this class is used to return an
        object of this class instead of a raw BER value in respvalue.
    """
    return self._ldap_call(self._l.extop,extreq.requestName,extreq.encodedRequestValue(),RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def extop_result(self,msgid=ldap.RES_ANY,all=1,timeout=None):
    resulttype,msg,msgid,respctrls,respoid,respvalue = self.result4(msgid,all=1,timeout=self.timeout,add_ctrls=1,add_intermediates=1,add_extop=1)
    return (respoid,respvalue)

  def extop_s(self,extreq,serverctrls=None,clientctrls=None,extop_resp_class=None):
    msgid = self.extop(extreq,serverctrls,clientctrls)
    res = self.extop_result(msgid,all=1,timeout=self.timeout)
    if extop_resp_class:
      respoid,respvalue = res
      if extop_resp_class.responseName!=respoid:
        raise ldap.PROTOCOL_ERROR(f"Wrong OID in extended response! Expected {extop_resp_class.responseName}, got {respoid}")
      return extop_resp_class(extop_resp_class.responseName,respvalue)
    else:
      return res

  def modify_ext(self,dn,modlist,serverctrls=None,clientctrls=None):
    """
    modify_ext(dn, modlist[,serverctrls=None[,clientctrls=None]]) -> int
    """
    return self._ldap_call(self._l.modify_ext,dn,modlist,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def modify_ext_s(self,dn,modlist,serverctrls=None,clientctrls=None):
    msgid = self.modify_ext(dn,modlist,serverctrls,clientctrls)
    resp_type, resp_data, resp_msgid, resp_ctrls = self.result3(msgid,all=1,timeout=self.timeout)
    return resp_type, resp_data, resp_msgid, resp_ctrls

  def modify(self,dn,modlist):
    """
    modify(dn, modlist) -> int
    modify_s(dn, modlist) -> None
    modify_ext(dn, modlist[,serverctrls=None[,clientctrls=None]]) -> int
    modify_ext_s(dn, modlist[,serverctrls=None[,clientctrls=None]]) -> tuple
        Performs an LDAP modify operation on an entry's attributes.
        dn is the DN of the entry to modify, and modlist is the list
        of modifications to make to the entry.

        Each element of the list modlist should be a tuple of the form
        (mod_op,mod_type,mod_vals), where mod_op is the operation (one of
        MOD_ADD, MOD_DELETE, MOD_INCREMENT or MOD_REPLACE), mod_type is a
        string indicating the attribute type name, and mod_vals is either a
        string value or a list of string values to add, delete, increment by or
        replace respectively.  For the delete operation, mod_vals may be None
        indicating that all attributes are to be deleted.

        The asynchronous modify() returns the message id of the
        initiated request.
    """
    return self.modify_ext(dn,modlist,None,None)

  def modify_s(self,dn,modlist):
    return self.modify_ext_s(dn,modlist,None,None)

  def modrdn(self,dn,newrdn,delold=1):
    """
    modrdn(dn, newrdn [,delold=1]) -> int
    modrdn_s(dn, newrdn [,delold=1]) -> None
        Perform a modify RDN operation. These routines take dn, the
        DN of the entry whose RDN is to be changed, and newrdn, the
        new RDN to give to the entry. The optional parameter delold
        is used to specify whether the old RDN should be kept as
        an attribute of the entry or not.  The asynchronous version
        returns the initiated message id.

        This operation is emulated by rename() and rename_s() methods
        since the modrdn2* routines in the C library are deprecated.
    """
    return self.rename(dn,newrdn,None,delold)

  def modrdn_s(self,dn,newrdn,delold=1):
    return self.rename_s(dn,newrdn,None,delold)

  def passwd(self,user,oldpw,newpw,serverctrls=None,clientctrls=None):
    return self._ldap_call(self._l.passwd,user,oldpw,newpw,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def passwd_s(self, user, oldpw, newpw, serverctrls=None, clientctrls=None, extract_newpw=False):
    msgid = self.passwd(user, oldpw, newpw, serverctrls, clientctrls)
    respoid, respvalue = self.extop_result(msgid, all=1, timeout=self.timeout)

    if respoid != PasswordModifyResponse.responseName:
      raise ldap.PROTOCOL_ERROR("Unexpected OID %s in extended response!" % respoid)
    if extract_newpw and respvalue:
      respvalue = PasswordModifyResponse(PasswordModifyResponse.responseName, respvalue)

    return respoid, respvalue

  def rename(self,dn,newrdn,newsuperior=None,delold=1,serverctrls=None,clientctrls=None):
    """
    rename(dn, newrdn [, newsuperior=None [,delold=1][,serverctrls=None[,clientctrls=None]]]) -> int
    rename_s(dn, newrdn [, newsuperior=None] [,delold=1][,serverctrls=None[,clientctrls=None]]) -> None
        Perform a rename entry operation. These routines take dn, the
        DN of the entry whose RDN is to be changed, newrdn, the
        new RDN, and newsuperior, the new parent DN, to give to the entry.
        If newsuperior is None then only the RDN is modified.
        The optional parameter delold is used to specify whether the
        old RDN should be kept as an attribute of the entry or not.
        The asynchronous version returns the initiated message id.

        This actually corresponds to the rename* routines in the
        LDAP-EXT C API library.
    """
    return self._ldap_call(self._l.rename,dn,newrdn,newsuperior,delold,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))

  def rename_s(self,dn,newrdn,newsuperior=None,delold=1,serverctrls=None,clientctrls=None):
    msgid = self.rename(dn,newrdn,newsuperior,delold,serverctrls,clientctrls)
    resp_type, resp_data, resp_msgid, resp_ctrls = self.result3(msgid,all=1,timeout=self.timeout)
    return resp_type, resp_data, resp_msgid, resp_ctrls

  def result(self,msgid=ldap.RES_ANY,all=1,timeout=None):
    """
    result([msgid=RES_ANY [,all=1 [,timeout=None]]]) -> (result_type, result_data)

        This method is used to wait for and return the result of an
        operation previously initiated by one of the LDAP asynchronous
        operation routines (e.g. search(), modify(), etc.) They all
        returned an invocation identifier (a message id) upon successful
        initiation of their operation. This id is guaranteed to be
        unique across an LDAP session, and can be used to request the
        result of a specific operation via the msgid parameter of the
        result() method.

        If the result of a specific operation is required, msgid should
        be set to the invocation message id returned when the operation
        was initiated; otherwise RES_ANY should be supplied.

        The all parameter only has meaning for search() responses
        and is used to select whether a single entry of the search
        response should be returned, or to wait for all the results
        of the search before returning.

        A search response is made up of zero or more search entries
        followed by a search result. If all is 0, search entries will
        be returned one at a time as they come in, via separate calls
        to result(). If all is 1, the search response will be returned
        in its entirety, i.e. after all entries and the final search
        result have been received.

        For all set to 0, result tuples
        trickle in (with the same message id), and with the result type
        RES_SEARCH_ENTRY, until the final result which has a result
        type of RES_SEARCH_RESULT and a (usually) empty data field.
        When all is set to 1, only one result is returned, with a
        result type of RES_SEARCH_RESULT, and all the result tuples
        listed in the data field.

        The method returns a tuple of the form (result_type,
        result_data).  The result_type is one of the constants RES_*.

        See search() for a description of the search result's
        result_data, otherwise the result_data is normally meaningless.

        The result() method will block for timeout seconds, or
        indefinitely if timeout is negative.  A timeout of 0 will effect
        a poll. The timeout can be expressed as a floating-point value.
        If timeout is None the default in self.timeout is used.

        If a timeout occurs, a TIMEOUT exception is raised, unless
        polling (timeout = 0), in which case (None, None) is returned.
    """
    resp_type, resp_data, resp_msgid = self.result2(msgid,all,timeout)
    return resp_type, resp_data

  def result2(self,msgid=ldap.RES_ANY,all=1,timeout=None):
    resp_type, resp_data, resp_msgid, resp_ctrls = self.result3(msgid,all,timeout)
    return resp_type, resp_data, resp_msgid

  def result3(self,msgid=ldap.RES_ANY,all=1,timeout=None,resp_ctrl_classes=None):
    resp_type, resp_data, resp_msgid, decoded_resp_ctrls, retoid, retval = self.result4(
      msgid,all,timeout,
      add_ctrls=0,add_intermediates=0,add_extop=0,
      resp_ctrl_classes=resp_ctrl_classes
    )
    return resp_type, resp_data, resp_msgid, decoded_resp_ctrls

  def result4(self,msgid=ldap.RES_ANY,all=1,timeout=None,add_ctrls=0,add_intermediates=0,add_extop=0,resp_ctrl_classes=None):
    if timeout is None:
      timeout = self.timeout
    ldap_result = self._ldap_call(self._l.result4,msgid,all,timeout,add_ctrls,add_intermediates,add_extop)
    if ldap_result is None:
        resp_type, resp_data, resp_msgid, resp_ctrls, resp_name, resp_value = (None,None,None,None,None,None)
    else:
      if len(ldap_result)==4:
        resp_type, resp_data, resp_msgid, resp_ctrls = ldap_result
        resp_name, resp_value = None,None
      else:
        resp_type, resp_data, resp_msgid, resp_ctrls, resp_name, resp_value = ldap_result
      if add_ctrls:
        resp_data = [ (t,r,DecodeControlTuples(c,resp_ctrl_classes)) for t,r,c in resp_data ]
    decoded_resp_ctrls = DecodeControlTuples(resp_ctrls,resp_ctrl_classes)
    return resp_type, resp_data, resp_msgid, decoded_resp_ctrls, resp_name, resp_value

  def search_ext(self,base,scope,filterstr=None,attrlist=None,attrsonly=0,serverctrls=None,clientctrls=None,timeout=-1,sizelimit=0):
    """
    search(base, scope [,filterstr='(objectClass=*)' [,attrlist=None [,attrsonly=0]]]) -> int
    search_s(base, scope [,filterstr='(objectClass=*)' [,attrlist=None [,attrsonly=0]]])
    search_st(base, scope [,filterstr='(objectClass=*)' [,attrlist=None [,attrsonly=0 [,timeout=-1]]]])
    search_ext(base,scope,[,filterstr='(objectClass=*)' [,attrlist=None [,attrsonly=0 [,serverctrls=None [,clientctrls=None [,timeout=-1 [,sizelimit=0]]]]]]])
    search_ext_s(base,scope,[,filterstr='(objectClass=*)' [,attrlist=None [,attrsonly=0 [,serverctrls=None [,clientctrls=None [,timeout=-1 [,sizelimit=0]]]]]]])

        Perform an LDAP search operation, with base as the DN of
        the entry at which to start the search, scope being one of
        SCOPE_BASE (to search the object itself), SCOPE_ONELEVEL
        (to search the object's immediate children), or SCOPE_SUBTREE
        (to search the object and all its descendants).

        filter is a string representation of the filter to
        apply in the search (see RFC 4515).

        Each result tuple is of the form (dn,entry), where dn is a
        string containing the DN (distinguished name) of the entry, and
        entry is a dictionary containing the attributes.
        Attributes types are used as string dictionary keys and attribute
        values are stored in a list as dictionary value.

        The DN in dn is extracted using the underlying ldap_get_dn(),
        which may raise an exception of the DN is malformed.

        If attrsonly is non-zero, the values of attrs will be
        meaningless (they are not transmitted in the result).

        The retrieved attributes can be limited with the attrlist
        parameter.  If attrlist is None, all the attributes of each
        entry are returned.

        serverctrls=None

        clientctrls=None

        The synchronous form with timeout, search_st() or search_ext_s(),
        will block for at most timeout seconds (or indefinitely if
        timeout is negative). A TIMEOUT exception is raised if no result is
        received within the time.

        The amount of search results retrieved can be limited with the
        sizelimit parameter if non-zero.
    """
    if filterstr is None:
      filterstr = '(objectClass=*)'
    return self._ldap_call(
      self._l.search_ext,
      base,scope,filterstr,
      attrlist,attrsonly,
      RequestControlTuples(serverctrls),
      RequestControlTuples(clientctrls),
      timeout,sizelimit,
    )

  def search_ext_s(self,base,scope,filterstr=None,attrlist=None,attrsonly=0,serverctrls=None,clientctrls=None,timeout=-1,sizelimit=0):
    msgid = self.search_ext(base,scope,filterstr,attrlist,attrsonly,serverctrls,clientctrls,timeout,sizelimit)
    return self.result(msgid,all=1,timeout=timeout)[1]

  def search(self,base,scope,filterstr=None,attrlist=None,attrsonly=0):
    return self.search_ext(base,scope,filterstr,attrlist,attrsonly,None,None)

  def search_s(self,base,scope,filterstr=None,attrlist=None,attrsonly=0):
    return self.search_ext_s(base,scope,filterstr,attrlist,attrsonly,None,None,timeout=self.timeout)

  def search_st(self,base,scope,filterstr=None,attrlist=None,attrsonly=0,timeout=-1):
    return self.search_ext_s(base,scope,filterstr,attrlist,attrsonly,None,None,timeout)

  def start_tls_s(self):
    """
    start_tls_s() -> None
    Negotiate TLS with server. The `version' attribute must have been
    set to VERSION3 before calling start_tls_s.
    If TLS could not be started an exception will be raised.
    """
    return self._ldap_call(self._l.start_tls_s)

  def unbind_ext(self,serverctrls=None,clientctrls=None):
    """
    unbind() -> int
    unbind_s() -> None
    unbind_ext() -> int
    unbind_ext_s() -> None
        This call is used to unbind from the directory, terminate
        the current association, and free resources. Once called, the
        connection to the LDAP server is closed and the LDAP object
        is invalid. Further invocation of methods on the object will
        yield an exception.

        The unbind and unbind_s methods are identical, and are
        synchronous in nature
    """
    res = self._ldap_call(self._l.unbind_ext,RequestControlTuples(serverctrls),RequestControlTuples(clientctrls))
    try:
      del self._l
    except AttributeError:
      pass
    return res

  def unbind_ext_s(self,serverctrls=None,clientctrls=None):
    msgid = self.unbind_ext(serverctrls,clientctrls)
    if msgid!=None:
      result = self.result3(msgid,all=1,timeout=self.timeout)
    else:
      result = None
    if __debug__ and self._trace_level>=1:
      try:
        self._trace_file.flush()
      except AttributeError:
        pass
    return result

  def unbind(self):
    return self.unbind_ext(None,None)

  def unbind_s(self):
    return self.unbind_ext_s(None,None)

  def whoami_s(self,serverctrls=None,clientctrls=None):
    return self._ldap_call(self._l.whoami_s,serverctrls,clientctrls)

  def get_option(self,option):
    result = self._ldap_call(self._l.get_option,option)
    if option==ldap.OPT_SERVER_CONTROLS or option==ldap.OPT_CLIENT_CONTROLS:
      result = DecodeControlTuples(result)
    return result

  def set_option(self,option,invalue):
    if option==ldap.OPT_SERVER_CONTROLS or option==ldap.OPT_CLIENT_CONTROLS:
      invalue = RequestControlTuples(invalue)
    return self._ldap_call(self._l.set_option,option,invalue)

  def search_subschemasubentry_s(self,dn=None):
    """
    Returns the distinguished name of the sub schema sub entry
    for a part of a DIT specified by dn.

    None as result indicates that the DN of the sub schema sub entry could
    not be determined.

    Returns: None or text/bytes depending on bytes_mode.
    """
    empty_dn = ''
    attrname = 'subschemaSubentry'
    if dn is None:
      dn = empty_dn
    try:
      r = self.search_s(
        dn,ldap.SCOPE_BASE,None,[attrname]
      )
    except (ldap.NO_SUCH_OBJECT,ldap.NO_SUCH_ATTRIBUTE,ldap.INSUFFICIENT_ACCESS):
      r = []
    except ldap.UNDEFINED_TYPE:
      return None
    try:
      if r:
        e = ldap.cidict.cidict(r[0][1])
        search_subschemasubentry_dn = e.get(attrname,[None])[0]
        if search_subschemasubentry_dn is None:
          if dn:
            # Try to find sub schema sub entry in root DSE
            return self.search_subschemasubentry_s(dn=empty_dn)
          else:
            # If dn was already root DSE we can return here
            return None
        else:
          if search_subschemasubentry_dn is not None:
            return search_subschemasubentry_dn.decode('utf-8')
    except IndexError:
      return None

  def read_s(self,dn,filterstr=None,attrlist=None,serverctrls=None,clientctrls=None,timeout=-1):
    """
    Reads and returns a single entry specified by `dn'.

    Other attributes just like those passed to `search_ext_s()'
    """
    r = self.search_ext_s(
      dn,
      ldap.SCOPE_BASE,
      filterstr,
      attrlist=attrlist,
      serverctrls=serverctrls,
      clientctrls=clientctrls,
      timeout=timeout,
    )
    if r:
      return r[0][1]
    else:
      return None

  def read_subschemasubentry_s(self,subschemasubentry_dn,attrs=None):
    """
    Returns the sub schema sub entry's data
    """
    filterstr = '(objectClass=subschema)'
    if attrs is None:
      attrs = SCHEMA_ATTRS
    try:
      subschemasubentry = self.read_s(
        subschemasubentry_dn,
        filterstr=filterstr,
        attrlist=attrs
      )
    except ldap.NO_SUCH_OBJECT:
      return None
    else:
      return subschemasubentry

  def find_unique_entry(self,base,scope=ldap.SCOPE_SUBTREE,filterstr=None,attrlist=None,attrsonly=0,serverctrls=None,clientctrls=None,timeout=-1):
    """
    Returns a unique entry, raises exception if not unique
    """
    r = self.search_ext_s(
      base,
      scope,
      filterstr,
      attrlist=attrlist,
      attrsonly=attrsonly,
      serverctrls=serverctrls,
      clientctrls=clientctrls,
      timeout=timeout,
      sizelimit=2,
    )
    if len(r)!=1:
      raise NO_UNIQUE_ENTRY('No or non-unique search result for %s' % (repr(filterstr)))
    return r[0]

  def read_rootdse_s(self, filterstr=None, attrlist=None):
    """
    convenience wrapper around read_s() for reading rootDSE
    """
    base = ''
    attrlist = attrlist or ['*', '+']
    ldap_rootdse = self.read_s(
      base,
      filterstr=filterstr,
      attrlist=attrlist,
    )
    return ldap_rootdse  # read_rootdse_s()

  def get_naming_contexts(self):
    """
    returns all attribute values of namingContexts in rootDSE
    if namingContexts is not present (not readable) then empty list is returned
    """
    name = 'namingContexts'
    return self.read_rootdse_s(
      attrlist=[name]
    ).get(name, [])


class ReconnectLDAPObject(SimpleLDAPObject):
  """
  :py:class:`SimpleLDAPObject` subclass whose synchronous request methods
  automatically reconnect and re-try in case of server failure
  (:exc:`ldap.SERVER_DOWN`).

  The first arguments are same as for the :py:func:`~ldap.initialize()`
  function.
  For automatic reconnects it has additional arguments:

  * retry_max: specifies the number of reconnect attempts before
    re-raising the :py:exc:`ldap.SERVER_DOWN` exception.

  * retry_delay: specifies the time in seconds between reconnect attempts.

  This class also implements the pickle protocol.
  """

  __transient_attrs__ = {
    '_l',
    '_ldap_object_lock',
    '_trace_file',
    '_reconnect_lock',
    '_last_bind',
  }

  def __init__(
    self,uri,
    trace_level=0,trace_file=None,trace_stack_limit=5,bytes_mode=None,
    bytes_strictness=None, retry_max=1, retry_delay=60.0, fileno=None
  ):
    """
    Parameters like SimpleLDAPObject.__init__() with these
    additional arguments:

    retry_max
        Maximum count of reconnect trials
    retry_delay
        Time span to wait between two reconnect trials
    """
    self._uri = uri
    self._options = []
    self._last_bind = None
    SimpleLDAPObject.__init__(self, uri, trace_level, trace_file,
                              trace_stack_limit, bytes_mode,
                              bytes_strictness=bytes_strictness,
                              fileno=fileno)
    self._reconnect_lock = ldap.LDAPLock(desc='reconnect lock within %s' % (repr(self)))
    self._retry_max = retry_max
    self._retry_delay = retry_delay
    self._start_tls = 0
    self._reconnects_done = 0

  def __getstate__(self):
    """return data representation for pickled object"""
    state = {
        k: v
        for k,v in self.__dict__.items()
        if k not in self.__transient_attrs__
    }
    state['_last_bind'] = self._last_bind[0].__name__, self._last_bind[1], self._last_bind[2]
    return state

  def __setstate__(self,d):
    """set up the object from pickled data"""
    hardfail = d.get('bytes_mode_hardfail')
    if hardfail:
        d.setdefault('bytes_strictness', 'error')
    else:
        d.setdefault('bytes_strictness', 'warn')
    self.__dict__.update(d)
    self._last_bind = getattr(SimpleLDAPObject, self._last_bind[0]), self._last_bind[1], self._last_bind[2]
    self._ldap_object_lock = self._ldap_lock()
    self._reconnect_lock = ldap.LDAPLock(desc='reconnect lock within %s' % (repr(self)))
    # XXX cannot pickle file, use default trace file
    self._trace_file = ldap._trace_file
    self.reconnect(self._uri)

  def _store_last_bind(self,method,*args,**kwargs):
    self._last_bind = (method,args,kwargs)

  def _apply_last_bind(self):
    if self._last_bind!=None:
      func,args,kwargs = self._last_bind
      func(self,*args,**kwargs)
    else:
      # Send explicit anon simple bind request to provoke ldap.SERVER_DOWN in method reconnect()
      SimpleLDAPObject.simple_bind_s(self, None, None)

  def _restore_options(self):
    """Restore all recorded options"""
    for k,v in self._options:
      SimpleLDAPObject.set_option(self,k,v)

  def passwd_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.passwd_s,*args,**kwargs)

  def reconnect(self,uri,retry_max=1,retry_delay=60.0):
    # Drop and clean up old connection completely
    # Reconnect
    self._reconnect_lock.acquire()
    try:
      reconnect_counter = retry_max
      while reconnect_counter:
        counter_text = '%d. (of %d)' % (retry_max-reconnect_counter+1,retry_max)
        if __debug__ and self._trace_level>=1:
          self._trace_file.write('*** Trying {} reconnect to {}...\n'.format(
            counter_text,uri
          ))
        try:
          try:
            # Do the connect
            self._l = ldap.functions._ldap_function_call(ldap._ldap_module_lock,_ldap.initialize,uri)
            self._restore_options()
            # StartTLS extended operation in case this was called before
            if self._start_tls:
              SimpleLDAPObject.start_tls_s(self)
            # Repeat last simple or SASL bind
            self._apply_last_bind()
          except ldap.LDAPError:
            SimpleLDAPObject.unbind_s(self)
            raise
        except (ldap.SERVER_DOWN,ldap.TIMEOUT):
          if __debug__ and self._trace_level>=1:
            self._trace_file.write('*** {} reconnect to {} failed\n'.format(
              counter_text,uri
            ))
          reconnect_counter = reconnect_counter-1
          if not reconnect_counter:
            raise
          if __debug__ and self._trace_level>=1:
            self._trace_file.write('=> delay %s...\n' % (retry_delay))
          time.sleep(retry_delay)
        else:
          if __debug__ and self._trace_level>=1:
            self._trace_file.write('*** {} reconnect to {} successful => repeat last operation\n'.format(
              counter_text,uri
            ))
          self._reconnects_done = self._reconnects_done + 1
          break
    finally:
      self._reconnect_lock.release()
    return # reconnect()

  def _apply_method_s(self,func,*args,**kwargs):
    if not hasattr(self,'_l'):
      self.reconnect(self._uri,retry_max=self._retry_max,retry_delay=self._retry_delay)
    try:
      return func(self,*args,**kwargs)
    except ldap.SERVER_DOWN:
      SimpleLDAPObject.unbind_s(self)
      # Try to reconnect
      self.reconnect(self._uri,retry_max=self._retry_max,retry_delay=self._retry_delay)
      # Re-try last operation
      return func(self,*args,**kwargs)

  def set_option(self,option,invalue):
    self._options.append((option,invalue))
    return SimpleLDAPObject.set_option(self,option,invalue)

  def bind_s(self,*args,**kwargs):
    res = self._apply_method_s(SimpleLDAPObject.bind_s,*args,**kwargs)
    self._store_last_bind(SimpleLDAPObject.bind_s,*args,**kwargs)
    return res

  def simple_bind_s(self,*args,**kwargs):
    res = self._apply_method_s(SimpleLDAPObject.simple_bind_s,*args,**kwargs)
    self._store_last_bind(SimpleLDAPObject.simple_bind_s,*args,**kwargs)
    return res

  def start_tls_s(self,*args,**kwargs):
    res = self._apply_method_s(SimpleLDAPObject.start_tls_s,*args,**kwargs)
    self._start_tls = 1
    return res

  def sasl_interactive_bind_s(self,*args,**kwargs):
    """
    sasl_interactive_bind_s(who, auth) -> None
    """
    res = self._apply_method_s(SimpleLDAPObject.sasl_interactive_bind_s,*args,**kwargs)
    self._store_last_bind(SimpleLDAPObject.sasl_interactive_bind_s,*args,**kwargs)
    return res

  def sasl_bind_s(self,*args,**kwargs):
    res = self._apply_method_s(SimpleLDAPObject.sasl_bind_s,*args,**kwargs)
    self._store_last_bind(SimpleLDAPObject.sasl_bind_s,*args,**kwargs)
    return res

  def add_ext_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.add_ext_s,*args,**kwargs)

  def cancel_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.cancel_s,*args,**kwargs)

  def compare_ext_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.compare_ext_s,*args,**kwargs)

  def delete_ext_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.delete_ext_s,*args,**kwargs)

  def extop_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.extop_s,*args,**kwargs)

  def modify_ext_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.modify_ext_s,*args,**kwargs)

  def rename_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.rename_s,*args,**kwargs)

  def search_ext_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.search_ext_s,*args,**kwargs)

  def whoami_s(self,*args,**kwargs):
    return self._apply_method_s(SimpleLDAPObject.whoami_s,*args,**kwargs)


# The class called LDAPObject will be used as default for
# ldap.open() and ldap.initialize()
LDAPObject = SimpleLDAPObject
